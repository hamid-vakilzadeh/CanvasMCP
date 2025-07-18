from typing import Union, Optional, TypedDict, List
from ..base import CanvasAPIBase


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


class QuizSubmissionFilesAPI(CanvasAPIBase):
    """Canvas LMS Quiz Submission Files API client for uploading files for quiz submissions."""

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Initialize the Canvas Quiz Submission Files API client.

        Args:
            access_token: Canvas API access token
            base_url: Canvas base URL (e.g., https://yourdomain.instructure.com)
        """
        super().__init__(access_token, base_url)

    def upload_quiz_submission_file(
        self,
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

        response = self._make_request(
            "POST",
            f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions/self/files",
            data=data,
        )
        return response.json()


# Lazy-loaded convenience instance
def get_quiz_submission_files():
    from ..base import access_token, url
    return QuizSubmissionFilesAPI(access_token, url)

class _LazyQuizSubmissionFilesAPI:
    def __getattr__(self, name):
        return getattr(get_quiz_submission_files(), name)

quiz_submission_files = _LazyQuizSubmissionFilesAPI()
