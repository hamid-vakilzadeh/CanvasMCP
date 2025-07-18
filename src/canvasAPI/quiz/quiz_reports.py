from typing import List, Dict, Union, Optional, Literal, TypedDict
from ..base import _make_request


class QuizReport(TypedDict, total=False):
    id: int
    quiz_id: int
    report_type: Literal["student_analysis", "item_analysis"]
    readable_type: str
    includes_all_versions: bool
    anonymous: bool
    generatable: bool
    created_at: str
    updated_at: str
    url: str
    file: Optional[Dict]
    progress_url: Optional[str]
    progress: Optional[Dict]


def list_quiz_reports(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    includes_all_versions: bool = False,
) -> List[QuizReport]:
    """
    Retrieve all quiz reports.

    Returns a list of all available reports.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        includes_all_versions: Whether to retrieve reports that consider all the submissions
                                or only the most recent. Defaults to false, ignored for item_analysis reports.

    Returns:
        List of quiz report dictionaries
    """
    params = {"includes_all_versions": includes_all_versions}

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/reports",
        params=params,
    )
    return response.json()


def create_quiz_report(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    report_type: Literal["student_analysis", "item_analysis"],
    includes_all_versions: bool = False,
    include: Optional[List[Literal["file", "progress"]]] = None,
) -> QuizReport:
    """
    Create a quiz report.

    Create and return a new report for this quiz. If a previously generated report
    matches the arguments and is still current (i.e. there have been no new submissions),
    it will be returned.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        report_type: The type of report to be generated ('student_analysis' or 'item_analysis')
        includes_all_versions: Whether the report should consider all submissions or only
                                the most recent. Defaults to false, ignored for item_analysis.
        include: Whether the output should include documents for the file and/or progress
                objects associated with this report. (Note: JSON-API only)

    Returns:
        Quiz report dictionary

    Raises:
        ValueError: If report_type is invalid
    """
    # Validate report_type
    valid_report_types = {"student_analysis", "item_analysis"}
    if report_type not in valid_report_types:
        raise ValueError(
            f"Invalid report_type '{report_type}'. "
            f"Allowed values: {', '.join(sorted(valid_report_types))}"
        )

    data = {
        "quiz_report[report_type]": report_type,
        "quiz_report[includes_all_versions]": includes_all_versions,
    }

    params = {}
    if include:
        # Validate include values
        valid_include_values = {"file", "progress"}
        for value in include:
            if value not in valid_include_values:
                raise ValueError(
                    f"Invalid include value '{value}'. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )
        params["include"] = include

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/reports",
        data=data,
        params=params,
    )
    return response.json()


def get_quiz_report(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    report_id: Union[int, str],
    include: Optional[List[Literal["file", "progress"]]] = None,
) -> QuizReport:
    """
    Get a quiz report.

    Returns the data for a single quiz report.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        report_id: Report ID
        include: Whether the output should include documents for the file and/or progress
                objects associated with this report. (Note: JSON-API only)

    Returns:
        Quiz report dictionary
    """
    params = {}
    if include:
        # Validate include values
        valid_include_values = {"file", "progress"}
        for value in include:
            if value not in valid_include_values:
                raise ValueError(
                    f"Invalid include value '{value}'. "
                    f"Allowed values: {', '.join(sorted(valid_include_values))}"
                )
        params["include"] = include

    response = _make_request(
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/reports/{report_id}",
        params=params,
    )
    return response.json()


def abort_quiz_report(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    quiz_id: Union[int, str],
    report_id: Union[int, str],
) -> None:
    """
    Abort the generation of a report, or remove a previously generated one.

    This API allows you to cancel a previous request you issued for a report to be generated.
    Or in the case of an already generated report, you'd like to remove it, perhaps to generate
    it another time with an updated version that provides new features.

    You must check the report's generation status before attempting to use this interface.
    See the "workflow_state" property of the QuizReport's Progress object for more information.
    Only when the progress reports itself in a "queued" state can the generation be aborted.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        quiz_id: Quiz ID
        report_id: Report ID

    Raises:
        RequestError: If the report is not being generated or cannot be aborted at this stage (422)
    """
    _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/courses/{course_id}/quizzes/{quiz_id}/reports/{report_id}",
    )
