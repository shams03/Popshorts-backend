from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os
import shutil
import json
from main import process_video
from features.autoUpload import upload_short
from models import ShortMetadata

app = FastAPI(
    title="PopShorts Backend API",
    description="Video processing and YouTube Shorts generation API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("shorts", exist_ok=True)
os.makedirs("temp_uploads", exist_ok=True)
app.mount("/shorts", StaticFiles(directory="shorts"), name="shorts")


# Request/Response Models
class ProcessVideoRequest(BaseModel):
    number_of_shorts: int
    auto_upload: bool = False
    mode: str = "sequential"


class ProcessVideoResponse(BaseModel):
    success: bool
    message: str
    shorts: List[dict]
    shorts_json_path: str


class UploadVideoRequest(BaseModel):
    video_path: str
    title: str
    description: str
    tags: List[str]
    privacy_status: Optional[str] = "public"


class UploadVideoResponse(BaseModel):
    success: bool
    message: str
    video_id: Optional[str] = None
    youtube_url: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {
        "status": "active",
        "message": "PopShorts API is running",
        "version": "1.0.0"
    }


@app.post("/process-video", response_model=ProcessVideoResponse)
async def process_video_endpoint(
    video: UploadFile = File(...),
    number_of_shorts: int = Form(...),
    auto_upload: bool = Form(False),
    mode: str = Form("sequential")
):
    """
    Process a video and generate YouTube Shorts
    
    Args:
        video: Video file to process
        number_of_shorts: Number of shorts to generate
        auto_upload: Whether to auto-upload to YouTube (requires credentials)
        mode: Processing mode (currently only 'sequential' is fully supported)
    
    Returns:
        ProcessVideoResponse with generated shorts and metadata
    """
    try:
        # Validate inputs
        if number_of_shorts < 1:
            raise HTTPException(status_code=400, detail="number_of_shorts must be at least 1")
        
        if mode not in ["sequential", "combined"]:
            raise HTTPException(status_code=400, detail="mode must be 'sequential' or 'combined'")
        
        # Create temp directory for uploaded video
        os.makedirs("temp_uploads", exist_ok=True)
        
        # Save uploaded file
        video_path = f"temp_uploads/{video.filename}"
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        # Process the video
        print(f"📹 Processing video: {video.filename}")
        shorts = process_video(
            file_path=video_path,
            upload=auto_upload,
            mode=mode,
            number=number_of_shorts
        )
        
        # Load the generated shorts.json
        shorts_json_path = os.path.join("shorts", "shorts.json")
        if os.path.exists(shorts_json_path):
            with open(shorts_json_path, "r") as f:
                final_shorts = json.load(f)
        else:
            final_shorts = shorts
        
        # Cleanup uploaded file
        if os.path.exists(video_path):
            os.remove(video_path)
        
        return ProcessVideoResponse(
            success=True,
            message=f"Successfully generated {len(final_shorts)} shorts",
            shorts=final_shorts,
            shorts_json_path=shorts_json_path
        )
    
    except Exception as e:
        print(f"❌ Error processing video: {str(e)}")
        
        # Cleanup on error
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing video: {str(e)}"
        )


@app.post("/upload-video", response_model=UploadVideoResponse)
async def upload_video_endpoint(request: UploadVideoRequest):
    """
    Upload a video to YouTube
    
    Args:
        request: UploadVideoRequest containing:
            - video_path: Path to the video file to upload
            - title: YouTube video title
            - description: YouTube video description
            - tags: List of tags/keywords
            - privacy_status: 'public', 'private', or 'unlisted' (default: 'public')
    
    Returns:
        UploadVideoResponse with YouTube video ID and URL
    
    Note: Requires valid YouTube OAuth credentials in secrets/client_secrets.json
    """
    try:
        # Validate file exists
        if not os.path.exists(request.video_path):
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found: {request.video_path}"
            )
        
        # Validate privacy status
        if request.privacy_status not in ["public", "private", "unlisted"]:
            raise HTTPException(
                status_code=400,
                detail="privacy_status must be 'public', 'private', or 'unlisted'"
            )
        
        # Check for credentials
        credentials_path = os.path.join("secrets", "client_secrets.json")
        if not os.path.exists(credentials_path):
            raise HTTPException(
                status_code=400,
                detail="YouTube credentials not found. Please set up OAuth credentials in secrets/client_secrets.json"
            )
        
        # TODO: Implement proper OAuth flow to get credentials
        # For now, this requires credentials to be set up separately
        # from google.auth.transport.requests import Request
        # from google.oauth2.service_account import Credentials
        # from google_auth_oauthlib.flow import InstalledAppFlow
        
        print(f"📤 Uploading video: {request.video_path}")
        
        # Note: Actual credentials loading and upload would be done here
        # This is a placeholder showing the expected flow
        raise HTTPException(
            status_code=501,
            detail="Upload functionality requires OAuth credentials setup. Please configure YouTube API credentials."
        )
        
        # Uncomment below once credentials are properly set up:
        # video_id = upload_short(
        #     credentials=credentials,
        #     video_path=request.video_path,
        #     title=request.title,
        #     description=request.description,
        #     tags=request.tags,
        #     privacy_status=request.privacy_status
        # )
        #
        # youtube_url = f"https://youtube.com/shorts/{video_id}"
        #
        # return UploadVideoResponse(
        #     success=True,
        #     message=f"Video uploaded successfully",
        #     video_id=video_id,
        #     youtube_url=youtube_url
        # )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading video: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading video: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PopShorts API"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )