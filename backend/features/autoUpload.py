# import os
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# def upload_short(
#     credentials,
#     video_path: str,
#     title: str,
#     description: str,
#     tags: list[str],
#     privacy_status: str = "public"
# ):
#     """
#     Upload a YouTube Short using WEB OAuth credentials
#     """

#     if not os.path.exists(video_path):
#         raise FileNotFoundError(f"Video not found: {video_path}")

#     if "#shorts" not in description.lower():
#         description += "\n\n#Shorts"

#     youtube = build("youtube", "v3", credentials=credentials)

#     body = {
#         "snippet": {
#             "title": title[:100],
#             "description": description,
#             "tags": tags,
#             "categoryId": "22"
#         },
#         "status": {
#             "privacyStatus": privacy_status,
#             "selfDeclaredMadeForKids": False
#         }
#     }

#     media = MediaFileUpload(
#         video_path,
#         mimetype="video/mp4",
#         resumable=True
#     )

#     request = youtube.videos().insert(
#         part="snippet,status",
#         body=body,
#         media_body=media
#     )

#     response = None
#     while response is None:
#         status, response = request.next_chunk()
#         if status:
#             print(f"Upload progress: {int(status.progress() * 100)}%")

#     print("✅ Upload successful!")
#     print(f"🎬 Video ID: {response['id']}")
#     print(f"🔗 https://youtube.com/shorts/{response['id']}")

#     return response["id"]

import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
import pickle

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def upload_short(
    credentials,
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str = "public"
):
    """
    Upload a YouTube Short using WEB OAuth credentials
    """

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    if "#shorts" not in description.lower():
        description += "\n\n#Shorts"

    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    print("✅ Upload successful!")
    print(f"🎬 Video ID: {response['id']}")
    print(f"🔗 https://youtube.com/shorts/{response['id']}")
    url = f"https://youtube.com/shorts/{response['id']}"

    return url



