from fastapi import FastAPI, UploadFile, HTTPException, File, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from mangum import Mangum
from typing import List, Optional
from ai.ai_agents import trademark_agent_runner, compliance_flow
from ai.rag import get_index, upsert_data, search_index, delete_vectors, get_paginated_vectors, get_vector, update_vector
from utils import get_base64_urls, get_docx_contents
import traceback

app = FastAPI(version="3.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse("/manage")

@app.get("/manage", response_class=HTMLResponse)
async def manage_rag(
    request: Request, 
    q: Optional[str] = None, 
    status: Optional[str] = None,
    page: int = 1,
    top_k: int = 12
):
    index = get_index()
    matches = []
    total_pages = 1
    if q:
        matches = search_index(index, q, top_k=top_k)
    else:
        matches, total_items = get_paginated_vectors(index,page,per_page=top_k)
        total_pages = (total_items + top_k - 1) // top_k
     
    return templates.TemplateResponse(
        "manage.html",
        {
            "request": request, 
            "query": q, 
            "matches": matches, 
            "status": status,
            "page": page,
            "top_k": top_k,
            "total_pages": total_pages
        }
    )

@app.get("/manage/delete/{vector_id}")
async def delete_document(vector_id: str):
    index = get_index()
    delete_vectors(index, [vector_id])
    return RedirectResponse(url="/manage?status=deleted")

@app.get("/manage/edit/{vector_id}", response_class=HTMLResponse)
async def edit_document_form(request: Request, vector_id: str):
    index = get_index()
    vector = get_vector(index, vector_id)
    if not vector:
        raise HTTPException(404, "Vector not found")
    metadata = vector['metadata']
    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "vector_id": vector_id,
            "text": metadata['Content'],
            "source": metadata['source']
        }
    )

@app.post("/manage/edit/{vector_id}")
async def update_document(
    vector_id: str,
    text: str = Form(...),
    source: str = Form(...)
):
    index = get_index()
    update_vector(index, vector_id, text, source)
    return RedirectResponse(url="/manage?status=updated", status_code=303)

@app.get("/manage/add", response_class=HTMLResponse)
async def add_document_form(request: Request):
    return templates.TemplateResponse("add.html", {"request": request})

@app.post("/manage/add")
async def add_new_document(
    source: str = Form(...),
    text: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None)
):
    index = get_index()
    contents = []
    
    if files:
        doc_contents = await get_docx_contents([files])
        for doc_content in doc_contents:
            contents.append({
                "text": doc_content,
                "source": source
            })
    elif text:
        contents.append({
            "text": text,
            "source": source
        })
    else:
        raise HTTPException(400, "Either text or DOCX file must be provided")
    
    if contents:
        upsert_data(index, contents)
    
    return RedirectResponse(url="/manage?status=added", status_code=303)



@app.post("/compliance-detect")
async def compliance_verification_flow(images: List[UploadFile] = File(..., description="Upload one or two image files for compliance verification.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        compliance_output = await compliance_flow(base64_urls)
        detection_output = await trademark_agent_runner(base64_urls)
        output = compliance_output | detection_output
    except HTTPException as e:
        traceback.print_exc()
        raise e
    except Exception as e:
        print(f"Error during compliance verification: {e}")
        traceback.print_exc()
        raise HTTPException(500,str(e))
    return output


@app.post("/compliance")
async def compliance_verification_flow(images: List[UploadFile] = File(..., description="Upload one or two image files for compliance verification.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        # output = await compliance_agent_runner(base64_urls)
        output = await compliance_flow(base64_urls)

    except HTTPException as e:
        traceback.print_exc()
        raise e
    except Exception as e:
        print(f"Error during compliance verification: {e}")
        traceback.print_exc()
        raise HTTPException(500,str(e))
    return output


@app.post("/trademark")
async def trademark_detection(images: List[UploadFile] = File(..., description="Upload one or two image files for trademark detection.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        output = await trademark_agent_runner(base64_urls)

    except HTTPException as e:
        traceback.print_exc()
        raise e
    except Exception as e:
        print(f"Error during trademark detection: {e}")
        traceback.print_exc()
        raise HTTPException(500,str(e))
    return {"output": output }



handler = Mangum(app)
