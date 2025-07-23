from typing import List, Dict, Union, Literal, Optional
from ..base import _make_request, _get_all_pages


def list_courses(
    base_url: str,
    access_token: str,
    enrollment_type: Optional[
        Literal["teacher", "student", "ta", "observer", "designer"]
    ] = None,
    enrollment_role: str = None,
    enrollment_role_id: int = None,
    enrollment_state: Optional[
        Literal["active", "invited_or_pending", "completed"]
    ] = None,
    exclude_blueprint_courses: bool = None,
    include: Optional[
        List[
            Literal[
                "needs_grading_count",
                "syllabus_body",
                "public_description",
                "total_scores",
                "current_grading_period_scores",
                "grading_periods",
                "term",
                "account",
                "course_progress",
                "sections",
                "storage_quota_used_mb",
                "total_students",
                "passback_status",
                "favorites",
                "teachers",
                "observed_users",
                "course_image",
                "banner_image",
                "concluded",
                "post_manually",
            ]
        ]
    ] = None,
    state: Optional[
        List[Literal["unpublished", "available", "completed", "deleted"]]
    ] = None,
    all_pages: bool = False,
) -> List[Dict]:
    """
    List courses for the current user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        enrollment_type: Filter by enrollment type (teacher, student, ta, observer, designer)
        enrollment_role: Filter by enrollment role (deprecated)
        enrollment_role_id: Filter by enrollment role ID
        enrollment_state: Filter by enrollment state (active, invited_or_pending, completed)
        exclude_blueprint_courses: Exclude blueprint courses
        include: Additional data to include (needs_grading_count, syllabus_body, public_description,
                total_scores, current_grading_period_scores, grading_periods, term, account,
                course_progress, sections, storage_quota_used_mb, total_students, passback_status,
                favorites, teachers, observed_users, course_image, banner_image, concluded, post_manually)
        state: Course states to include (unpublished, available, completed, deleted)
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of course dictionaries

    Raises:
        ValueError: If enrollment_type, enrollment_state, state, or include values are invalid
    """
    # Validate enrollment_type
    if enrollment_type is not None:
        valid_enrollment_types = {
            "teacher",
            "student",
            "ta",
            "observer",
            "designer",
        }
        if enrollment_type not in valid_enrollment_types:
            raise ValueError(
                f"Invalid enrollment_type '{enrollment_type}'. "
                f"Allowed values: {', '.join(sorted(valid_enrollment_types))}"
            )

    # Validate enrollment_state
    if enrollment_state is not None:
        valid_enrollment_states = {"active", "invited_or_pending", "completed"}
        if enrollment_state not in valid_enrollment_states:
            raise ValueError(
                f"Invalid enrollment_state '{enrollment_state}'. "
                f"Allowed values: {', '.join(sorted(valid_enrollment_states))}"
            )

    # Validate state values
    if state is not None:
        valid_course_states = {"unpublished", "available", "completed", "deleted"}
        invalid_states = [s for s in state if s not in valid_course_states]
        if invalid_states:
            raise ValueError(
                f"Invalid state values: {', '.join(invalid_states)}. "
                f"Allowed values: {', '.join(sorted(valid_course_states))}"
            )

    # Validate include values
    if include is not None:
        valid_include_values = {
            "needs_grading_count",
            "syllabus_body",
            "public_description",
            "total_scores",
            "current_grading_period_scores",
            "grading_periods",
            "term",
            "account",
            "course_progress",
            "sections",
            "storage_quota_used_mb",
            "total_students",
            "passback_status",
            "favorites",
            "teachers",
            "observed_users",
            "course_image",
            "banner_image",
            "concluded",
            "post_manually",
        }
        invalid_includes = [i for i in include if i not in valid_include_values]
        if invalid_includes:
            raise ValueError(
                f"Invalid include values: {', '.join(invalid_includes)}. "
                f"Allowed values: {', '.join(sorted(valid_include_values))}"
            )

    params = {}

    if enrollment_type:
        params["enrollment_type"] = enrollment_type
    if enrollment_role:
        params["enrollment_role"] = enrollment_role
    if enrollment_role_id:
        params["enrollment_role_id"] = enrollment_role_id
    if enrollment_state:
        params["enrollment_state"] = enrollment_state
    if exclude_blueprint_courses is not None:
        params["exclude_blueprint_courses"] = exclude_blueprint_courses
    if include:
        params["include[]"] = include
    if state:
        params["state[]"] = state

    if all_pages:
        return _get_all_pages(
            base_url, access_token, "GET", "/api/v1/courses", params=params
        )
    else:
        response = _make_request(
            base_url, access_token, "GET", "/api/v1/courses", params=params
        )
        return response.json()


def list_courses_for_user(
    base_url: str,
    access_token: str,
    user_id: Union[int, str],
    include: Optional[
        List[
            Literal[
                "needs_grading_count",
                "syllabus_body",
                "public_description",
                "total_scores",
                "current_grading_period_scores",
                "grading_periods",
                "term",
                "account",
                "course_progress",
                "sections",
                "storage_quota_used_mb",
                "total_students",
                "passback_status",
                "favorites",
                "teachers",
                "observed_users",
                "course_image",
                "banner_image",
                "concluded",
                "post_manually",
            ]
        ]
    ] = None,
    state: Optional[
        List[Literal["unpublished", "available", "completed", "deleted"]]
    ] = None,
    enrollment_state: Optional[
        Literal["active", "invited_or_pending", "completed"]
    ] = None,
    homeroom: bool = None,
    account_id: str = None,
    all_pages: bool = False,
) -> List[Dict]:
    """
    List courses for a specific user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        user_id: User ID or 'self'
        include: Additional data to include (needs_grading_count, syllabus_body, public_description,
                total_scores, current_grading_period_scores, grading_periods, term, account,
                course_progress, sections, storage_quota_used_mb, total_students, passback_status,
                favorites, teachers, observed_users, course_image, banner_image, concluded, post_manually)
        state: Course states to include (unpublished, available, completed, deleted)
        enrollment_state: Filter by enrollment state (active, invited_or_pending, completed)
        homeroom: Filter homeroom courses
        account_id: Filter by account ID
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of course dictionaries
    """
    # Validate enrollment_state
    if enrollment_state is not None:
        valid_enrollment_states = {"active", "invited_or_pending", "completed"}
        if enrollment_state not in valid_enrollment_states:
            raise ValueError(
                f"Invalid enrollment_state '{enrollment_state}'. "
                f"Allowed values: {', '.join(sorted(valid_enrollment_states))}"
            )

    # Validate state values
    if state is not None:
        valid_course_states = {"unpublished", "available", "completed", "deleted"}
        invalid_states = [s for s in state if s not in valid_course_states]
        if invalid_states:
            raise ValueError(
                f"Invalid state values: {', '.join(invalid_states)}. "
                f"Allowed values: {', '.join(sorted(valid_course_states))}"
            )

    # Validate include values
    if include is not None:
        valid_include_values = {
            "needs_grading_count",
            "syllabus_body",
            "public_description",
            "total_scores",
            "current_grading_period_scores",
            "grading_periods",
            "term",
            "account",
            "course_progress",
            "sections",
            "storage_quota_used_mb",
            "total_students",
            "passback_status",
            "favorites",
            "teachers",
            "observed_users",
            "course_image",
            "banner_image",
            "concluded",
            "post_manually",
        }
        invalid_includes = [i for i in include if i not in valid_include_values]
        if invalid_includes:
            raise ValueError(
                f"Invalid include values: {', '.join(invalid_includes)}. "
                f"Allowed values: {', '.join(sorted(valid_include_values))}"
            )

    params = {}

    if include:
        params["include[]"] = include
    if state:
        params["state[]"] = state
    if enrollment_state:
        params["enrollment_state"] = enrollment_state
    if homeroom is not None:
        params["homeroom"] = homeroom
    if account_id:
        params["account_id"] = account_id

    if all_pages:
        return _get_all_pages(
            "GET",
            f"/api/v1/users/{user_id}/courses",
            params=params,
        )
    else:
        response = _make_request(
            "GET",
            f"/api/v1/users/{user_id}/courses",
            params=params,
        )
        return response.json()


def get_course(
    course_id: Union[int, str],
    include: List[str] = None,
    teacher_limit: int = None,
) -> Dict:
    """
    Get information about a single course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        include: Additional data to include
        teacher_limit: Maximum number of teacher enrollments to show

    Returns:
        Course dictionary
    """
    params = {}

    if include:
        params["include[]"] = include
    if teacher_limit:
        params["teacher_limit"] = teacher_limit

    response = _make_request("GET", f"/api/v1/courses/{course_id}", params=params)
    return response.json()


# Course Management Methods


def create_course(
    account_id: Union[int, str],
    course_data: Dict,
    offer: bool = False,
    enroll_me: bool = False,
) -> Dict:
    """
    Create a new course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID to create course in
        course_data: Course configuration data
        offer: Make course available to students immediately
        enroll_me: Enroll current user as teacher

    Returns:
        Created course dictionary
    """
    data = {}

    # Add course data with proper prefixes
    for key, value in course_data.items():
        data[f"course[{key}]"] = value

    if offer:
        data["offer"] = offer
    if enroll_me:
        data["enroll_me"] = enroll_me

    response = _make_request(
        "POST",
        f"/api/v1/accounts/{account_id}/courses",
        data=data,
    )
    return response.json()


def update_course(
    course_id: Union[int, str],
    course_data: Dict,
    offer: bool = None,
    override_sis_stickiness: bool = True,
) -> Dict:
    """
    Update an existing course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        course_data: Course configuration data to update
        offer: Make course available to students
        override_sis_stickiness: Override SIS sticky fields

    Returns:
        Updated course dictionary
    """
    data = {}

    # Add course data with proper prefixes
    for key, value in course_data.items():
        data[f"course[{key}]"] = value

    if offer is not None:
        data["offer"] = offer
    if override_sis_stickiness is not None:
        data["override_sis_stickiness"] = override_sis_stickiness

    response = _make_request("PUT", f"/api/v1/courses/{course_id}", data=data)
    return response.json()


def delete_conclude_course(course_id: Union[int, str], event: str) -> Dict:
    """
    Delete or conclude a course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        event: Action to take ('delete' or 'conclude')

    Returns:
        Result dictionary
    """
    data = {"event": event}
    response = _make_request("DELETE", f"/api/v1/courses/{course_id}", data=data)
    return response.json()


def batch_update_courses(
    account_id: Union[int, str],
    course_ids: List[str],
    event: str,
) -> Dict:
    """
    Update multiple courses in an account.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        course_ids: List of course IDs (max 500)
        event: Action to take (offer, conclude, delete, undelete)

    Returns:
        Progress object
    """
    data = {"course_ids[]": course_ids, "event": event}
    response = _make_request(
        "PUT",
        f"/api/v1/accounts/{account_id}/courses",
        data=data,
    )
    return response.json()


def reset_course_content(course_id: Union[int, str]) -> Dict:
    """
    Reset course content (deletes current course and creates new equivalent).

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        New course dictionary
    """
    response = _make_request("POST", f"/api/v1/courses/{course_id}/reset_content")
    return response.json()


# Course Users Methods


def list_course_users(
    course_id: Union[int, str],
    search_term: str = None,
    sort: Literal["username", "last_login", "email", "sis_id"] = None,
    enrollment_type: Optional[
        List[
            Literal[
                "teacher",
                "student",
                "student_view",
                "ta",
                "observer",
                "designer",
            ]
        ]
    ] = None,
    enrollment_role: str = None,
    enrollment_role_id: int = None,
    include: List[
        Literal[
            "enrollments",
            "locked",
            "avatar_url",
            "test_student",
            "bio",
            "custom_links",
            "current_grading_period_scores",
            "uuid",
        ]
    ] = None,
    user_id: str = None,
    user_ids: List[int] = None,
    enrollment_state: Optional[
        List[
            Literal[
                "active",
                "invited",
                "rejected",
                "completed",
                "inactive",
            ]
        ]
    ] = None,
    all_pages: bool = False,
) -> List[Dict]:
    """
    List users in a course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        search_term: Search term for user names/IDs
        sort: Sort field (username, last_login, email, sis_id)
        enrollment_type: Filter by enrollment type (teacher, student, ta, observer, designer)
        enrollment_role: Filter by enrollment role
        enrollment_role_id: Filter by enrollment role ID
        include: Additional data to include
        user_id: Specific user ID to find
        user_ids: List of specific user IDs
        enrollment_state: Filter by enrollment state (active, invited_or_pending, completed)
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of user dictionaries

    Raises:
        ValueError: If enrollment_type or enrollment_state values are invalid
    """
    # Validate enrollment_type values
    if enrollment_type is not None:
        valid_enrollment_types = {
            "teacher",
            "student",
            "student_view",
            "ta",
            "observer",
            "designer",
        }
        invalid_enrollment_types = [
            e for e in enrollment_type if e not in valid_enrollment_types
        ]
        if invalid_enrollment_types:
            raise ValueError(
                f"Invalid enrollment_type values: {', '.join(invalid_enrollment_types)}. "
                f"Allowed values: {', '.join(sorted(valid_enrollment_types))}"
            )

    # Validate enrollment_state values
    if enrollment_state is not None:
        valid_enrollment_states = {"active", "invited_or_pending", "completed"}
        invalid_enrollment_states = [
            e for e in enrollment_state if e not in valid_enrollment_states
        ]
        if invalid_enrollment_states:
            raise ValueError(
                f"Invalid enrollment_state values: {', '.join(invalid_enrollment_states)}. "
                f"Allowed values: {', '.join(sorted(valid_enrollment_states))}"
            )

    params = {}

    if search_term:
        params["search_term"] = search_term
    if sort:
        params["sort"] = sort
    if enrollment_type:
        params["enrollment_type[]"] = enrollment_type
    if enrollment_role:
        params["enrollment_role"] = enrollment_role
    if enrollment_role_id:
        params["enrollment_role_id"] = enrollment_role_id
    if include:
        params["include[]"] = include
    if user_id:
        params["user_id"] = user_id
    if user_ids:
        params["user_ids[]"] = user_ids
    if enrollment_state:
        params["enrollment_state[]"] = enrollment_state

    if all_pages:
        return _get_all_pages(
            "GET",
            f"/api/v1/courses/{course_id}/users",
            params=params,
        )
    else:
        response = _make_request(
            "GET",
            f"/api/v1/courses/{course_id}/users",
            params=params,
        )
        return response.json()


def get_course_user(
    course_id: Union[int, str],
    user_id: Union[int, str],
    include: List[str] = None,
) -> Dict:
    """
    Get single user in course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        user_id: User ID
        include: Additional data to include

    Returns:
        User dictionary
    """
    params = {}
    if include:
        params["include[]"] = include

    response = _make_request(
        "GET",
        f"/api/v1/courses/{course_id}/users/{user_id}",
        params=params,
    )
    return response.json()


def list_students(
    course_id: Union[int, str],
    all_pages: bool = False,
) -> List[Dict]:
    """
    List students in course (DEPRECATED - use list_course_users instead).

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of student dictionaries
    """
    if all_pages:
        return _get_all_pages("GET", f"/api/v1/courses/{course_id}/students")
    else:
        response = _make_request("GET", f"/api/v1/courses/{course_id}/students")
        return response.json()


def list_recent_students(
    course_id: Union[int, str],
    all_pages: bool = False,
) -> List[Dict]:
    """
    List recently logged in students.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of student dictionaries with last_login
    """
    if all_pages:
        return _get_all_pages(
            "GET",
            f"/api/v1/courses/{course_id}/recent_students",
        )
    else:
        response = _make_request(
            "GET",
            f"/api/v1/courses/{course_id}/recent_students",
        )
        return response.json()


def search_content_share_users(
    course_id: Union[int, str],
    search_term: str,
    all_pages: bool = False,
) -> List[Dict]:
    """
    Search for users to share content with.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        search_term: Search term
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of user dictionaries
    """
    data = {"search_term": search_term}
    if all_pages:
        return _get_all_pages(
            "GET",
            f"/api/v1/courses/{course_id}/content_share_users",
            data=data,
        )
    else:
        response = _make_request(
            "GET",
            f"/api/v1/courses/{course_id}/content_share_users",
            data=data,
        )
        return response.json()


# Course Progress Methods


def get_user_progress(
    course_id: Union[int, str],
    user_id: Union[int, str],
) -> Dict:
    """
    Get user progress in course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        user_id: User ID or 'self'

    Returns:
        CourseProgress dictionary
    """
    response = _make_request(
        "GET",
        f"/api/v1/courses/{course_id}/users/{user_id}/progress",
    )
    return response.json()


def get_bulk_user_progress(course_id: Union[int, str]) -> List[Dict]:
    """
    Get progress for all users in course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        List of user progress dictionaries
    """
    response = _make_request("GET", f"/api/v1/courses/{course_id}/bulk_user_progress")
    return response.json()


# Course Settings Methods


def get_course_settings(course_id: Union[int, str]) -> Dict:
    """
    Get course settings.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        Course settings dictionary
    """
    response = _make_request("GET", f"/api/v1/courses/{course_id}/settings")
    return response.json()


def update_course_settings(course_id: Union[int, str], settings: Dict) -> Dict:
    """
    Update course settings.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        settings: Settings to update

    Returns:
        Updated settings dictionary
    """
    response = _make_request(
        "PUT",
        f"/api/v1/courses/{course_id}/settings",
        data=settings,
    )
    return response.json()


# Course Activity Methods


def get_activity_stream(
    course_id: Union[int, str],
    all_pages: bool = False,
) -> List[Dict]:
    """
    Get course activity stream for current user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of activity items
    """
    if all_pages:
        return _get_all_pages(
            "GET",
            f"/api/v1/courses/{course_id}/activity_stream",
        )
    else:
        response = _make_request(
            "GET",
            f"/api/v1/courses/{course_id}/activity_stream",
        )
        return response.json()


def get_activity_stream_summary(course_id: Union[int, str]) -> Dict:
    """
    Get course activity stream summary.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        Activity summary dictionary
    """
    response = _make_request(
        "GET",
        f"/api/v1/courses/{course_id}/activity_stream/summary",
    )
    return response.json()


def get_todo_items(course_id: Union[int, str]) -> List[Dict]:
    """
    Get course TODO items for current user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        List of TODO items
    """
    response = _make_request("GET", f"/api/v1/courses/{course_id}/todo")
    return response.json()


# Utility Methods


def preview_html(course_id: Union[int, str], html: str) -> Dict:
    """
    Preview HTML content processed for course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        html: HTML content to process

    Returns:
        Processed HTML dictionary
    """
    data = {"html": html}
    response = _make_request(
        "POST",
        f"/api/v1/courses/{course_id}/preview_html",
        data=data,
    )
    return response.json()


def upload_file(course_id: Union[int, str], **kwargs) -> Dict:
    """
    Start file upload process for course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        **kwargs: File upload parameters

    Returns:
        Upload response dictionary
    """
    response = _make_request(
        "POST",
        f"/api/v1/courses/{course_id}/files",
        data=kwargs,
    )
    return response.json()


def get_student_view_student(course_id: Union[int, str]) -> Dict:
    """
    Get or create test student for course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        Test student user dictionary
    """
    response = _make_request(
        "GET",
        f"/api/v1/courses/{course_id}/student_view_student",
    )
    return response.json()


def get_effective_due_dates(
    course_id: Union[int, str],
    assignment_ids: List[str] = None,
) -> Dict:
    """
    Get effective due dates for course assignments.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        assignment_ids: List of assignment IDs to filter

    Returns:
        Due dates dictionary
    """
    params = {}
    if assignment_ids:
        params["assignment_ids[]"] = assignment_ids

    response = _make_request(
        "GET",
        f"/api/v1/courses/{course_id}/effective_due_dates",
        params=params,
    )
    return response.json()


def get_permissions(course_id: Union[int, str], permissions: List[str]) -> Dict:
    """
    Check permissions for current user in course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        permissions: List of permissions to check

    Returns:
        Permissions dictionary
    """
    data = {"permissions[]": permissions}
    response = _make_request(
        "GET",
        f"/api/v1/courses/{course_id}/permissions",
        data=data,
    )
    return response.json()


def dismiss_migration_alert(course_id: Union[int, str]) -> Dict:
    """
    Dismiss quiz migration limitation alert.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        Success dictionary
    """
    response = _make_request(
        "POST",
        f"/api/v1/courses/{course_id}/dismiss_migration_limitation_message",
    )
    return response.json()


# Course Copy Methods (DEPRECATED)


def get_course_copy_status(
    course_id: Union[int, str],
    copy_id: Union[int, str],
) -> Dict:
    """
    Get course copy status (DEPRECATED - use Content Migrations API).

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        copy_id: Copy operation ID

    Returns:
        Copy status dictionary
    """
    response = _make_request(
        "GET",
        f"/api/v1/courses/{course_id}/course_copy/{copy_id}",
    )
    return response.json()


def copy_course_content(
    course_id: Union[int, str],
    source_course: str,
    except_types: List[str] = None,
    only_types: List[str] = None,
) -> Dict:
    """
    Copy content from another course (DEPRECATED - use Content Migrations API).

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Destination course ID
        source_course: Source course ID or SIS-ID
        except_types: Content types to exclude
        only_types: Content types to include (exclusive with except_types)

    Returns:
        Copy operation dictionary
    """
    data = {"source_course": source_course}

    if except_types:
        data["except[]"] = except_types
    if only_types:
        data["only[]"] = only_types

    response = _make_request(
        "POST",
        f"/api/v1/courses/{course_id}/course_copy",
        data=data,
    )
    return response.json()
