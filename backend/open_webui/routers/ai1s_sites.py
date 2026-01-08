from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
import logging
import json
import traceback
from pathlib import Path
from fastapi import UploadFile
from starlette.datastructures import Headers
from open_webui.models.files import Files, FileModel, FileForm
from open_webui.models.knowledge import Knowledges, KnowledgeForm
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.routers.retrieval import process_file, ProcessFileForm, AI_SITES_FILE_ID_PREFIX
from open_webui.models.ai1s_sites import get_wp_post_with_meta_by_id, get_all_wp_posts_with_meta
from open_webui.utils.auth import get_admin_user
from open_webui.utils.access_control import has_access
from open_webui.constants import ERROR_MESSAGES
from open_webui.storage.provider import Storage
import uuid
import io
from open_webui.routers.files import upload_file_handler
from open_webui.routers.knowledge import add_file_to_knowledge_by_id, create_new_knowledge

log = logging.getLogger(__name__)

router = APIRouter()

class ImportPostForm(BaseModel):
    post_id: str

class ImportAllPostsForm(BaseModel):
    limit: Optional[int] = None

def html_to_text(html_content: str) -> str:
    """Convert HTML content to clean plain text"""
    if not html_content:
        return ""
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style tags
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    return text


def html_to_markdown(html_content: str) -> str:
    """Convert HTML content to clean Markdown using BeautifulSoup"""
    if not html_content:
        return ""
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style tags
    for tag in soup(["script", "style"]):
        tag.decompose()
    
    def convert_element(element):
        """Recursively convert HTML element to Markdown"""
        if element.name is None:
            # Text node - just return stripped text
            return element.strip() if isinstance(element, str) else ""
        
        # Process children first
        children = []
        for child in element.children:
            if isinstance(child, str):
                child_text = child.strip()
                if child_text:
                    children.append(child_text)
            else:
                child_md = convert_element(child)
                if child_md:
                    children.append(child_md)
        
        # Join children with spaces, but avoid extra spaces
        content = " ".join(children).strip()
        if not content:
            return ""
        
        # Convert based on tag name
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(element.name[1])
            return f"{'#' * level} {content}\n\n"
        elif element.name == "p":
            return f"{content}\n\n"
        elif element.name in ["strong", "b"]:
            return f"**{content}**"
        elif element.name in ["em", "i"]:
            return f"*{content}*"
        elif element.name == "ul":
            # Process list items
            markdown = ""
            for li in element.find_all("li", recursive=False):
                li_md = convert_element(li)
                if li_md:
                    markdown += f"- {li_md}\n"
            return f"{markdown}\n"
        elif element.name == "ol":
            # Process ordered list items
            markdown = ""
            for i, li in enumerate(element.find_all("li", recursive=False), 1):
                li_md = convert_element(li)
                if li_md:
                    markdown += f"{i}. {li_md}\n"
            return f"{markdown}\n"
        elif element.name == "li":
            # Just return content for li (parent handles the list marker)
            return content
        elif element.name == "br":
            return "\n"
        elif element.name == "a":
            href = element.get("href", "#")
            return f"[{content}]({href})"
        else:
            # Default case - just return content
            return content
    
    # Process all top-level elements
    markdown = ""
    for child in soup.body.children if soup.body else soup.children:
        if not isinstance(child, str):
            child_md = convert_element(child)
            if child_md:
                markdown += child_md
    
    # Clean up whitespace
    import re
    # markdown = re.sub(r'\s+', ' ', markdown)  # Normalize whitespace
    markdown = re.sub(r'\s*\n\s*', '\n', markdown)  # Clean line breaks
    # markdown = re.sub(r'\n{3,}', '\n\n', markdown)  # Max 2 newlines
    markdown = markdown.strip()  # Strip leading/trailing whitespace
    
    return markdown

async def import_single_post_to_knowledge(
    request: Request,
    knowledge_id: str,
    post_id: str,
    post_data: dict,
    user=None,
    knowledge=None,  # Pass existing knowledge object to avoid duplicate queries
    knowledge_files=[]
):
    try:
        # Check if file already exists
        file_id = f"{AI_SITES_FILE_ID_PREFIX}{post_id}"
        existing_file = Files.get_file_by_id(file_id)
        
        # If file exist, remove it
        if existing_file:
            log.error(f"existing_file:{existing_file}")
            try:
                # Remove the file's collection from vector database
                file_collection = f"file-{file_id}"
                log.error(f"file_collection:{file_collection}")
                log.error(f"before has_collection:{VECTOR_DB_CLIENT.has_collection(collection_name=file_collection)}")
                VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection)
            except Exception as e:
                log.debug("This was most likely caused by bypassing embedding processing")
                log.debug(e)
                log.error(f"delete file failed:{e}")
                pass
            # Delete file from database
            Files.delete_file_by_id(file_id)

        if True:
            # Convert post content to text file
            # clean_content = html_to_text(post_data['post_content'])
            clean_content = html_to_markdown(post_data['post_content'])
            markdown_content = html_to_markdown(post_data['post_content'])
            clean_description = post_data.get('site_description', clean_content[:200] + '...')
            content = f"Name: {post_data['post_name']}\n"
            content += f"Description: {clean_description}\n"
            content += f"Content: {clean_content}\n"
            if True: # just for debug
                log.error(f"=== POST {post_id} CONVERSION RESULTS ===")
                log.error(f"Original HTML (first 300 chars): {post_data['post_content'][:300]}...")
                log.error(f"Plain Text (first 300 chars): {clean_content[:300]}...")
                log.error(f"Markdown (first 300 chars): {markdown_content[:300]}...")
                log.error(f"Full Markdown: {markdown_content}")
            # content += f"URL: {post_data['guid']}\n"
            
            # # Add metadata
            # if post_data.get('meta_key') and post_data.get('meta_value'):
            #     content += f"\nMeta Data:\n{post_data['meta_key']}: {post_data['meta_value']}\n"
            
            # Create file
            filename = f"{file_id}.txt"
            
            # Use upload_file_handler to create file
            file_obj = io.BytesIO(content.encode('utf-8'))
            headers = Headers({"content-type": "text/plain"})
            upload_file = UploadFile(
                file=file_obj,
                filename=filename,
                headers=headers
            )
            log.error(f"passed in file_id:{file_id}")
            
            # Use upload_file_handler to create file
            file_item = upload_file_handler(
                request,
                file=upload_file,
                metadata={"post_id": post_id},
                process=True,
                # process=False, # TODO test fix embedding twice
                process_in_background=False,
                user=user,
                id=file_id
            )
            log.error(f"[test]upload_file_handler result file_item:{file_item}")
            file_id = file_item["id"]
            log.error(f"result file_id:{file_id}")
        
        # Check if file is already in knowledge base
        file_in_knowledge = any(file.id == file_id for file in knowledge_files)
        if not file_in_knowledge:
            # Add file to knowledge base
            from open_webui.routers.knowledge import KnowledgeFileIdForm
            await add_file_to_knowledge_by_id(
                request,
                id=knowledge_id,
                form_data=KnowledgeFileIdForm(file_id=file_id),
                user=user
            )
        
        return {
            "post_id": post_id,
            "file_id": file_id,
            "status": "success"
        }
        
    except Exception as e:
        log.error(f"Error importing post {post_id}: {traceback.format_exc()}")
        return {
            "post_id": post_id,
            "status": "error",
            "message": str(e)
        }

@router.post("/{id}/import/post")
async def import_post_to_knowledge(
    request: Request,
    id: str,
    form_data: ImportPostForm,
    user=Depends(get_admin_user)
):
    try:
        # Get WordPress post
        log.info(f"Importing post {form_data.post_id} to knowledge base {id}")
        post = get_wp_post_with_meta_by_id(form_data.post_id)
        log.info(f"get_wp_post_with_meta_by_id result: {post}")
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post {form_data.post_id} not found"
            )
        knowledge = Knowledges.get_knowledge_by_id(id)
        knowledge_files = Knowledges.get_files_by_id(id)
        # Use common function to import post
        result = await import_single_post_to_knowledge(
            request,
            id,
            form_data.post_id,
            post,
            user,
            knowledge,
            knowledge_files
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "post_id": result["post_id"],
                "file_id": result["file_id"],
                "message": f"Post {result['post_id']} imported successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error importing post: {result['message']}"
            )
        
    except Exception as e:
        log.error(f"Error importing post: {str(e)}, traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing post: {str(e)}"
        )

import asyncio
from open_webui.tasks import create_task
from bs4 import BeautifulSoup
import re

# Global variable to track import progress
import_progress = {}

@router.get("/{id}/import/progress/{task_id}")
async def get_import_progress(
    request: Request,
    id: str,
    task_id: str,
    user=Depends(get_admin_user)
):
    try:
        if task_id not in import_progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        progress = import_progress[task_id]
        return {
            "task_id": task_id,
            "total_post_num": progress["total_post_num"],
            "processed_post_num": progress["processed_post_num"],
            "status": progress["status"],
            "results": progress.get("results", [])
        }
        
    except Exception as e:
        log.error(f"Error getting import progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting import progress: {str(e)}"
        )

@router.post("/{id}/import/all")
async def import_all_posts_to_knowledge(
    request: Request,
    id: str,
    form_data: Optional[ImportAllPostsForm] = None,
    user=Depends(get_admin_user)
):
    try:
        # 获取所有WordPress文章
        posts = get_all_wp_posts_with_meta()
        if not posts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No posts found"
            )
        
        # 限制导入数量
        if form_data and form_data.limit:
            posts = posts[:form_data.limit]
        
        # Initialize progress tracking
        task_id = str(uuid.uuid4())
        import_progress[task_id] = {
            "total_post_num": len(posts),
            "processed_post_num": 0,
            "status": "running",
            "results": []
        }
        
        # Define background task
        async def import_task():
            try:
                knowledge = Knowledges.get_knowledge_by_id(id)
                knowledge_files = Knowledges.get_files_by_id(id)
                
                for post in posts:
                    try:
                        # Use common function to import post, passing existing knowledge object
                        result = await import_single_post_to_knowledge(
                            request,
                            id,
                            post['ID'],
                            post,
                            user,
                            knowledge,  # Pass existing knowledge to avoid duplicate queries
                            knowledge_files
                        )
                        import_progress[task_id]["results"].append(result)
                        
                    except Exception as e:
                        log.error(f"Error importing post {post['ID']}: {str(e)}")
                        import_progress[task_id]["results"].append({
                            "post_id": post['ID'],
                            "status": "error",
                            "message": str(e)
                        })
                    finally:
                        import_progress[task_id]["processed_post_num"] += 1
                
                import_progress[task_id]["status"] = "completed"
                
            except Exception as e:
                log.error(f"Error importing all posts: {str(e)}")
                import_progress[task_id]["status"] = "error"
                import_progress[task_id]["error"] = str(e)
        
        # Create background task
        await create_task(request.app.state.redis, import_task(), id)
        
        return {
            "task_id": task_id,
            "total_post_num": len(posts),
            "message": "Import task started successfully"
        }
        
    except Exception as e:
        log.error(f"Error starting import task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting import task: {str(e)}"
        )

@router.get("/{id}/import/statistics")
async def get_all_posts_importing_statistics(
    request: Request,
    id: str,
    user=Depends(get_admin_user)
):
    try:
        posts = get_all_wp_posts_with_meta()
        knowledge_files = Knowledges.get_files_by_id(id)
        log.error(f"posts num: {len(posts)}, knowledge_files num: {len(knowledge_files)}")
        statistics = {
            "total_post_num": len(posts),
            "knowledge_files_num": len(knowledge_files),
        }
        return statistics
    except Exception as e:
        log.error(f"Error getting posts importing statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting posts importing statistics: {str(e)}"
        )
