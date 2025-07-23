from typing import Union, Optional, TypedDict, List
from ..base import _make_request


class FileUploadParams(TypedDict, total=False):
    key: str
    acl: str
    Filename: str
    AWSAccessKeyId: str
    Policy: str
    Signature: str
    Content_Type: str


class FileUploadAttachment(TypedDict):
    upload_url: str
    upload_params: FileUploadParams


class FileUploadResponse(TypedDict):
    attachments: List[FileUploadAttachment]


def upload_quiz_submission_file(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    name: str,
    on_duplicate: Optional[str] = None,
) -> FileUploadResponse:
    """
    Upload a file for quiz submission.

    Associate a new quiz submission file. This API endpoint is the first step in uploading
    a quiz submission file. See the File Upload Documentation for details on the file upload
    workflow as these parameters are interpreted as per the documentation there.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        name: The name of the quiz submission file
        on_duplicate: How to handle duplicate names (optional)

    Returns:
        Dictionary containing file upload information:
        - attachments: List of attachment objects with upload_url and upload_params
            - upload_url: The URL to upload the file to (e.g., S3 bucket URL)
            - upload_params: Parameters needed for the upload including:
            - key: File path/key for the upload
            - acl: Access control level
            - Filename: The filename
            - AWSAccessKeyId: AWS access key for upload
            - Policy: Upload policy string
            - Signature: Upload signature
            - Content-Type: MIME type of the file

    Note:
        This endpoint returns upload parameters for a two-step upload process. After receiving
        the response, you need to use the upload_url and upload_params to actually upload
        the file to the specified location (typically S3).
    """
    data = {"name": name}

    if on_duplicate is not None:
        data["on_duplicate"] = on_duplicate

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/self/files",
        data=data,
    )
    return response.json()
