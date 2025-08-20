from typing import List, Dict, Union, Literal, Optional, TypedDict
from datetime import datetime
from ..base import _make_request, _get_all_pages


class Term(TypedDict, total=False):
    """Term object"""

    id: int
    name: str
    start_at: Optional[str]
    end_at: Optional[str]


class CourseProgress(TypedDict, total=False):
    """Course Progress object"""

    requirement_count: int
    requirement_completed_count: int
    next_requirement_url: Optional[str]
    completed_at: Optional[str]


class BlueprintRestriction(TypedDict, total=False):
    """Blueprint Restriction object"""

    content: bool
    points: bool
    due_dates: bool
    availability_dates: bool


class Course(TypedDict, total=False):
    """Course object"""

    id: int
    sis_course_id: Optional[str]
    uuid: str
    integration_id: Optional[str]
    sis_import_id: Optional[int]
    name: str
    course_code: str
    original_name: Optional[str]
    workflow_state: Literal["unpublished", "available", "completed", "deleted"]
    account_id: int
    root_account_id: int
    enrollment_term_id: int
    grading_periods: Optional[List[Dict]]
    grading_standard_id: Optional[int]
    grade_passback_setting: Optional[str]
    created_at: str
    start_at: Optional[str]
    end_at: Optional[str]
    locale: Optional[str]
    enrollments: Optional[List[Dict]]
    total_students: Optional[int]
    calendar: Optional[Dict]
    default_view: Literal["feed", "wiki", "modules", "assignments", "syllabus"]
    syllabus_body: Optional[str]
    needs_grading_count: Optional[int]
    term: Optional[Term]
    course_progress: Optional[CourseProgress]
    apply_assignment_group_weights: bool
    permissions: Optional[Dict]
    is_public: bool
    is_public_to_auth_users: bool
    public_syllabus: bool
    public_syllabus_to_auth: bool
    public_description: Optional[str]
    storage_quota_mb: int
    storage_quota_used_mb: Optional[int]
    hide_final_grades: bool
    license: Optional[str]
    allow_student_assignment_edits: bool
    allow_wiki_comments: bool
    allow_student_forum_attachments: bool
    open_enrollment: bool
    self_enrollment: bool
    restrict_enrollments_to_course_dates: bool
    course_format: Optional[str]
    access_restricted_by_date: bool
    time_zone: str
    blueprint: Optional[bool]
    blueprint_restrictions: Optional[BlueprintRestriction]
    blueprint_restrictions_by_object_type: Optional[Dict[str, BlueprintRestriction]]
    template: Optional[bool]


def list_courses(
    base_url: str,
    access_token: str,
    enrollment_type: Optional[
        Literal["teacher", "student", "ta", "observer", "designer"]
    ] = None,
    enrollment_role: Optional[str] = None,
    enrollment_role_id: Optional[int] = None,
    enrollment_state: Optional[
        Literal["active", "invited_or_pending", "completed"]
    ] = None,
    exclude_blueprint_courses: Optional[bool] = None,
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
                "tabs",
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
) -> List[Course]:
    """
    Returns the paginated list of active courses for the current user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        enrollment_type: When set, only return courses where the user is enrolled as this type.
                        For example, set to "teacher" to return only courses where the user is
                        enrolled as a Teacher. This argument is ignored if enrollment_role is given.
        enrollment_role: DEPRECATED - When set, only return courses where the user is enrolled
                        with the specified course-level role. This can be a role created with the
                        Add Role API or a base role type of 'StudentEnrollment', 'TeacherEnrollment',
                        'TaEnrollment', 'ObserverEnrollment', or 'DesignerEnrollment'.
        enrollment_role_id: When set, only return courses where the user is enrolled with the
                           specified course-level role ID. This can be a role created with the
                           Add Role API or a built-in role type.
        enrollment_state: When set, only return courses where the user has an enrollment with
                         the given state. This will respect section/course/term date overrides.
        exclude_blueprint_courses: When set, only return courses that are not configured as
                                  blueprint courses.
        include: Optional information to include with each Course:
                - "needs_grading_count": Total number of submissions needing grading for all assignments
                - "syllabus_body": User-generated HTML for the course syllabus
                - "public_description": User-generated text for the course public description
                - "total_scores": Student enrollment grade fields (computed_current_score, etc.)
                - "current_grading_period_scores": Current grading period grade information
                - "grading_periods": List of grading periods associated with each course
                - "term": Information for the enrollment term for each course
                - "account": Account JSON for each course
                - "course_progress": Progress through the course (requirement counts, completion)
                - "sections": Section enrollment information
                - "storage_quota_used_mb": Amount of storage space used by files in course
                - "total_students": Integer for total amount of active and invited students
                - "passback_status": Include the grade passback_status
                - "favorites": Indicates if user has marked course as favorite
                - "teachers": Teacher information for each course
                - "observed_users": Data for observed users if current user has observer enrollment
                - "tabs": List of tabs configured for each course
                - "course_image": Course image URL if set
                - "banner_image": Course banner image URL if set (Canvas for Elementary)
                - "concluded": Whether course has been concluded
                - "post_manually": Course post policy setting (manual vs automatic)
        state: If set, only return courses that are in the given state(s). By default, "available"
              is returned for students and observers, and anything except "deleted" for all other
              enrollment types.
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of Course dictionaries

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
            "tabs",
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
                "tabs",
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
    homeroom: Optional[bool] = None,
    account_id: Optional[str] = None,
    all_pages: bool = False,
) -> List[Course]:
    """
    Returns a paginated list of active courses for this user. To view the course list for a user 
    other than yourself, you must be either an observer of that user or an administrator.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        user_id: User ID or 'self' to get courses for the current user
        include: Optional information to include with each Course (same options as list_courses)
        state: If set, only return courses that are in the given state(s). By default, "available" 
              is returned for students and observers, and anything except "deleted" for all other 
              enrollment types.
        enrollment_state: When set, only return courses where the user has an enrollment with 
                         the given state. This will respect section/course/term date overrides.
        homeroom: If set to true, only return homeroom courses.
        account_id: If set, only include courses associated with this account.
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of Course dictionaries
        
    Raises:
        ValueError: If enrollment_state, state, or include values are invalid
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
            "tabs",
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
            base_url,
            access_token,
            "GET",
            f"/api/v1/users/{user_id}/courses",
            params=params,
        )
    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/users/{user_id}/courses",
            params=params,
        )
        return response.json()


def get_course(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    include: Optional[
        List[
            Literal[
                "needs_grading_count",
                "syllabus_body",
                "public_description",
                "total_scores",
                "current_grading_period_scores",
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
                "all_courses",
                "permissions",
                "course_image",
                "banner_image",
                "concluded",
                "lti_context_id",
                "post_manually",
            ]
        ]
    ] = None,
    teacher_limit: Optional[int] = None,
) -> Course:
    """
    Return information on a single course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        include: Optional information to include with the Course:
                - "needs_grading_count": Total number of submissions needing grading
                - "syllabus_body": User-generated HTML for the course syllabus  
                - "public_description": User-generated text for the course public description
                - "total_scores": Student enrollment grade fields
                - "current_grading_period_scores": Current grading period grade information
                - "term": Information for the enrollment term for the course
                - "account": Account JSON for the course
                - "course_progress": Progress through the course
                - "sections": Section enrollment information
                - "storage_quota_used_mb": Amount of storage space used by files
                - "total_students": Integer for total amount of active and invited students
                - "passback_status": Include the grade passback_status
                - "favorites": Indicates if user has marked course as favorite
                - "teachers": Teacher information for the course
                - "observed_users": Data for observed users if current user has observer enrollment
                - "all_courses": Also search recently deleted courses
                - "permissions": Include permissions the current user has for the course
                - "course_image": Include course image URL if set
                - "banner_image": Include course banner image URL if set (Canvas for Elementary)
                - "concluded": Whether course has been concluded
                - "lti_context_id": Include course LTI tool ID
                - "post_manually": Include course post policy setting
        teacher_limit: The maximum number of teacher enrollments to show. If the course 
                      contains more teachers than this, instead of giving the teacher 
                      enrollments, the count of teachers will be given under a teacher_count key.

    Returns:
        Course dictionary

    Raises:
        ValueError: If include values are invalid
    """
    # Validate include values
    if include is not None:
        valid_include_values = {
            "needs_grading_count",
            "syllabus_body",
            "public_description",
            "total_scores",
            "current_grading_period_scores",
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
            "all_courses",
            "permissions",
            "course_image",
            "banner_image",
            "concluded",
            "lti_context_id",
            "post_manually",
        }
        invalid_includes = [i for i in include if i not in valid_include_values]
        if invalid_includes:
            raise ValueError(
                f"Invalid include values: {', '.join(invalid_includes)}. "
                f"Allowed values: {', '.join(sorted(valid_include_values))}"
            )

    # Validate teacher_limit
    if teacher_limit is not None and teacher_limit < 0:
        raise ValueError("teacher_limit must be non-negative")

    params = {}

    if include:
        params["include[]"] = include
    if teacher_limit is not None:
        params["teacher_limit"] = teacher_limit

    response = _make_request(
        base_url, access_token, "GET", f"/api/v1/courses/{course_id}", params=params
    )
    return response.json()


# Course Management Methods


def create_course(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    name: Optional[str] = None,
    course_code: Optional[str] = None,
    start_at: Optional[str] = None,
    end_at: Optional[str] = None,
    license: Optional[
        Literal[
            "private",
            "cc_by_nc_nd",
            "cc_by_nc_sa",
            "cc_by_nc",
            "cc_by_nd",
            "cc_by_sa", 
            "cc_by",
            "public_domain",
        ]
    ] = None,
    is_public: Optional[bool] = None,
    is_public_to_auth_users: Optional[bool] = None,
    public_syllabus: Optional[bool] = None,
    public_syllabus_to_auth: Optional[bool] = None,
    public_description: Optional[str] = None,
    allow_student_wiki_edits: Optional[bool] = None,
    allow_wiki_comments: Optional[bool] = None,
    allow_student_forum_attachments: Optional[bool] = None,
    open_enrollment: Optional[bool] = None,
    self_enrollment: Optional[bool] = None,
    restrict_enrollments_to_course_dates: Optional[bool] = None,
    term_id: Optional[Union[int, str]] = None,
    sis_course_id: Optional[str] = None,
    integration_id: Optional[str] = None,
    hide_final_grades: Optional[bool] = None,
    apply_assignment_group_weights: Optional[bool] = None,
    time_zone: Optional[str] = None,
    default_view: Optional[
        Literal["feed", "wiki", "modules", "syllabus", "assignments"]
    ] = None,
    syllabus_body: Optional[str] = None,
    grading_standard_id: Optional[int] = None,
    grade_passback_setting: Optional[str] = None,
    course_format: Optional[Literal["on_campus", "online", "blended"]] = None,
    post_manually: Optional[bool] = None,
    offer: bool = False,
    enroll_me: bool = False,
    skip_course_template: bool = False,
    enable_sis_reactivation: bool = False,
) -> Course:
    """
    Create a new course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID to create course in
        name: The name of the course. If omitted, the course will be named "Unnamed Course."
        course_code: The course code for the course
        start_at: Course start date in ISO8601 format (e.g. 2011-01-01T01:00Z). 
                 This value is ignored unless 'restrict_enrollments_to_course_dates' is set to true
        end_at: Course end date in ISO8601 format (e.g. 2011-01-01T01:00Z). 
               This value is ignored unless 'restrict_enrollments_to_course_dates' is set to true
        license: The name of the licensing. Should be one of the abbreviations:
                'private' (Private Copyrighted), 'cc_by_nc_nd' (CC Attribution Non-Commercial No Derivatives),
                'cc_by_nc_sa' (CC Attribution Non-Commercial Share Alike), 'cc_by_nc' (CC Attribution Non-Commercial),
                'cc_by_nd' (CC Attribution No Derivatives), 'cc_by_sa' (CC Attribution Share Alike),
                'cc_by' (CC Attribution), 'public_domain' (Public Domain)
        is_public: Set to true if course is public to both authenticated and unauthenticated users
        is_public_to_auth_users: Set to true if course is public only to authenticated users
        public_syllabus: Set to true to make the course syllabus public
        public_syllabus_to_auth: Set to true to make the course syllabus public for authenticated users
        public_description: A publicly visible description of the course
        allow_student_wiki_edits: If true, students will be able to modify the course wiki
        allow_wiki_comments: If true, course members will be able to comment on wiki pages
        allow_student_forum_attachments: If true, students can attach files to forum posts
        open_enrollment: Set to true if the course is open enrollment
        self_enrollment: Set to true if the course is self enrollment
        restrict_enrollments_to_course_dates: Set to true to restrict user enrollments to the start 
                                             and end dates of the course. This value must be set to 
                                             true in order to specify a course start date and/or end date
        term_id: The unique ID of the term to create to course in
        sis_course_id: The unique SIS identifier
        integration_id: The unique Integration identifier
        hide_final_grades: If this option is set to true, the totals in student grades summary will be hidden
        apply_assignment_group_weights: Set to true to weight final grade based on assignment groups percentages
        time_zone: The time zone for the course. Allowed time zones are IANA time zones or friendlier 
                  Ruby on Rails time zones
        default_view: The type of page that users will see when they first visit the course:
                     'feed' Recent Activity Dashboard, 'wiki' Wiki Front Page, 'modules' Course Modules/Sections Page,
                     'assignments' Course Assignments List, 'syllabus' Course Syllabus Page
        syllabus_body: The syllabus body for the course
        grading_standard_id: The grading standard id to set for the course. If no value is provided 
                            for this argument the current grading_standard will be un-set from this course
        grade_passback_setting: Optional. The grade_passback_setting for the course. Only 'nightly_sync', 
                               'disabled', and empty string are allowed
        course_format: Optional. Specifies the format of the course. Should be 'on_campus', 'online', or 'blended'
        post_manually: Default is false. When true, all grades in the course must be posted manually, 
                      and will not be automatically posted. When false, all grades in the course will 
                      be automatically posted
        offer: If this option is set to true, the course will be available to students immediately
        enroll_me: Set to true to enroll the current user as the teacher
        skip_course_template: If this option is set to true, the template of the account will not 
                             be applied to this course
        enable_sis_reactivation: When true, will first try to re-activate a deleted course with 
                                matching sis_course_id if possible

    Returns:
        Created Course dictionary

    Raises:
        ValueError: If validation fails for license, default_view, course_format, or other parameters
    """
    # Validate license
    if license is not None:
        valid_licenses = {
            "private",
            "cc_by_nc_nd",
            "cc_by_nc_sa",
            "cc_by_nc",
            "cc_by_nd",
            "cc_by_sa",
            "cc_by",
            "public_domain",
        }
        if license not in valid_licenses:
            raise ValueError(
                f"Invalid license '{license}'. "
                f"Allowed values: {', '.join(sorted(valid_licenses))}"
            )

    # Validate default_view
    if default_view is not None:
        valid_default_views = {"feed", "wiki", "modules", "syllabus", "assignments"}
        if default_view not in valid_default_views:
            raise ValueError(
                f"Invalid default_view '{default_view}'. "
                f"Allowed values: {', '.join(sorted(valid_default_views))}"
            )

    # Validate course_format
    if course_format is not None:
        valid_course_formats = {"on_campus", "online", "blended"}
        if course_format not in valid_course_formats:
            raise ValueError(
                f"Invalid course_format '{course_format}'. "
                f"Allowed values: {', '.join(sorted(valid_course_formats))}"
            )

    # Validate grading_standard_id
    if grading_standard_id is not None and grading_standard_id < 0:
        raise ValueError("grading_standard_id must be non-negative")

    data = {}

    # Add all course parameters  
    if name is not None:
        data["course[name]"] = name
    if course_code is not None:
        data["course[course_code]"] = course_code
    if start_at is not None:
        data["course[start_at]"] = start_at
    if end_at is not None:
        data["course[end_at]"] = end_at
    if license is not None:
        data["course[license]"] = license
    if is_public is not None:
        data["course[is_public]"] = is_public
    if is_public_to_auth_users is not None:
        data["course[is_public_to_auth_users]"] = is_public_to_auth_users
    if public_syllabus is not None:
        data["course[public_syllabus]"] = public_syllabus
    if public_syllabus_to_auth is not None:
        data["course[public_syllabus_to_auth]"] = public_syllabus_to_auth
    if public_description is not None:
        data["course[public_description]"] = public_description
    if allow_student_wiki_edits is not None:
        data["course[allow_student_wiki_edits]"] = allow_student_wiki_edits
    if allow_wiki_comments is not None:
        data["course[allow_wiki_comments]"] = allow_wiki_comments
    if allow_student_forum_attachments is not None:
        data["course[allow_student_forum_attachments]"] = allow_student_forum_attachments
    if open_enrollment is not None:
        data["course[open_enrollment]"] = open_enrollment
    if self_enrollment is not None:
        data["course[self_enrollment]"] = self_enrollment
    if restrict_enrollments_to_course_dates is not None:
        data["course[restrict_enrollments_to_course_dates]"] = restrict_enrollments_to_course_dates
    if term_id is not None:
        data["course[term_id]"] = term_id
    if sis_course_id is not None:
        data["course[sis_course_id]"] = sis_course_id
    if integration_id is not None:
        data["course[integration_id]"] = integration_id
    if hide_final_grades is not None:
        data["course[hide_final_grades]"] = hide_final_grades
    if apply_assignment_group_weights is not None:
        data["course[apply_assignment_group_weights]"] = apply_assignment_group_weights
    if time_zone is not None:
        data["course[time_zone]"] = time_zone
    if default_view is not None:
        data["course[default_view]"] = default_view
    if syllabus_body is not None:
        data["course[syllabus_body]"] = syllabus_body
    if grading_standard_id is not None:
        data["course[grading_standard_id]"] = grading_standard_id
    if grade_passback_setting is not None:
        data["course[grade_passback_setting]"] = grade_passback_setting
    if course_format is not None:
        data["course[course_format]"] = course_format
    if post_manually is not None:
        data["course[post_manually]"] = post_manually

    if offer:
        data["offer"] = offer
    if enroll_me:
        data["enroll_me"] = enroll_me
    if skip_course_template:
        data["skip_course_template"] = skip_course_template
    if enable_sis_reactivation:
        data["enable_sis_reactivation"] = enable_sis_reactivation

    response = _make_request(
        base_url,
        access_token,
        "POST",
        f"/api/v1/accounts/{account_id}/courses",
        data=data,
    )
    return response.json()


def update_course(
    base_url: str,
    access_token: str,
    course_id: Union[int, str],
    account_id: Optional[int] = None,
    name: Optional[str] = None,
    course_code: Optional[str] = None,
    start_at: Optional[str] = None,
    end_at: Optional[str] = None,
    license: Optional[
        Literal[
            "private",
            "cc_by_nc_nd",
            "cc_by_nc_sa",
            "cc_by_nc",
            "cc_by_nd",
            "cc_by_sa",
            "cc_by",
            "public_domain",
        ]
    ] = None,
    is_public: Optional[bool] = None,
    is_public_to_auth_users: Optional[bool] = None,
    public_syllabus: Optional[bool] = None,
    public_syllabus_to_auth: Optional[bool] = None,
    public_description: Optional[str] = None,
    allow_student_wiki_edits: Optional[bool] = None,
    allow_wiki_comments: Optional[bool] = None,
    allow_student_forum_attachments: Optional[bool] = None,
    open_enrollment: Optional[bool] = None,
    self_enrollment: Optional[bool] = None,
    restrict_enrollments_to_course_dates: Optional[bool] = None,
    term_id: Optional[int] = None,
    sis_course_id: Optional[str] = None,
    integration_id: Optional[str] = None,
    hide_final_grades: Optional[bool] = None,
    time_zone: Optional[str] = None,
    apply_assignment_group_weights: Optional[bool] = None,
    storage_quota_mb: Optional[int] = None,
    event: Optional[
        Literal["claim", "offer", "conclude", "delete", "undelete"]
    ] = None,
    default_view: Optional[
        Literal["feed", "wiki", "modules", "syllabus", "assignments"]
    ] = None,
    syllabus_body: Optional[str] = None,
    syllabus_course_summary: Optional[bool] = None,
    grading_standard_id: Optional[int] = None,
    grade_passback_setting: Optional[str] = None,
    course_format: Optional[Literal["on_campus", "online"]] = None,
    image_id: Optional[int] = None,
    image_url: Optional[str] = None,
    remove_image: Optional[bool] = None,
    remove_banner_image: Optional[bool] = None,
    blueprint: Optional[bool] = None,
    blueprint_restrictions: Optional[Dict] = None,
    use_blueprint_restrictions_by_object_type: Optional[bool] = None,
    blueprint_restrictions_by_object_type: Optional[Dict] = None,
    homeroom_course: Optional[bool] = None,
    sync_enrollments_from_homeroom: Optional[str] = None,
    homeroom_course_id: Optional[str] = None,
    template: Optional[bool] = None,
    course_color: Optional[str] = None,
    friendly_name: Optional[str] = None,
    enable_course_paces: Optional[bool] = None,
    conditional_release: Optional[bool] = None,
    post_manually: Optional[bool] = None,
    offer: Optional[bool] = None,
    override_sis_stickiness: bool = True,
) -> Course:
    """
    Update an existing course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID
        account_id: The unique ID of the account to move the course to
        name: The name of the course. If omitted, the course will be named "Unnamed Course."
        course_code: The course code for the course
        start_at: Course start date in ISO8601 format (e.g. 2011-01-01T01:00Z). 
                 This value is ignored unless 'restrict_enrollments_to_course_dates' is set to true,
                 or the course is already published
        end_at: Course end date in ISO8601 format (e.g. 2011-01-01T01:00Z). 
               This value is ignored unless 'restrict_enrollments_to_course_dates' is set to true
        license: The name of the licensing. Should be one of the abbreviations:
                'private' (Private Copyrighted), 'cc_by_nc_nd' (CC Attribution Non-Commercial No Derivatives),
                'cc_by_nc_sa' (CC Attribution Non-Commercial Share Alike), 'cc_by_nc' (CC Attribution Non-Commercial),
                'cc_by_nd' (CC Attribution No Derivatives), 'cc_by_sa' (CC Attribution Share Alike),
                'cc_by' (CC Attribution), 'public_domain' (Public Domain)
        is_public: Set to true if course is public to both authenticated and unauthenticated users
        is_public_to_auth_users: Set to true if course is public only to authenticated users
        public_syllabus: Set to true to make the course syllabus public
        public_syllabus_to_auth: Set to true to make the course syllabus to public for authenticated users
        public_description: A publicly visible description of the course
        allow_student_wiki_edits: If true, students will be able to modify the course wiki
        allow_wiki_comments: If true, course members will be able to comment on wiki pages
        allow_student_forum_attachments: If true, students can attach files to forum posts
        open_enrollment: Set to true if the course is open enrollment
        self_enrollment: Set to true if the course is self enrollment
        restrict_enrollments_to_course_dates: Set to true to restrict user enrollments to the start 
                                             and end dates of the course. Setting this value to false 
                                             will remove the course end date (if it exists), as well as 
                                             the course start date (if the course is unpublished)
        term_id: The unique ID of the term to create to course in
        sis_course_id: The unique SIS identifier
        integration_id: The unique Integration identifier
        hide_final_grades: If this option is set to true, the totals in student grades summary will be hidden
        time_zone: The time zone for the course. Allowed time zones are IANA time zones or friendlier 
                  Ruby on Rails time zones
        apply_assignment_group_weights: Set to true to weight final grade based on assignment groups percentages
        storage_quota_mb: Set the storage quota for the course, in megabytes. The caller must have 
                         the "Manage storage quotas" account permission
        event: The action to take on the course:
               'claim' makes a course no longer visible to students. This action is also called 
               "unpublish" on the web site. A course cannot be unpublished if students have received 
               graded submissions.
               'offer' makes a course visible to students. This action is also called "publish" on the web site.
               'conclude' prevents future enrollments and makes a course read-only for all participants. 
               The course still appears in prior-enrollment lists.
               'delete' completely removes the course from the web site (including course menus and 
               prior-enrollment lists). All enrollments are deleted. Course content may be physically 
               deleted at a future date.
               'undelete' attempts to recover a course that has been deleted. This action requires 
               account administrative rights. (Recovery is not guaranteed; please conclude rather than 
               delete a course if there is any possibility the course will be used again.) The recovered 
               course will be unpublished. Deleted enrollments will not be recovered.
        default_view: The type of page that users will see when they first visit the course:
                     'feed' Recent Activity Dashboard, 'wiki' Wiki Front Page, 'modules' Course Modules/Sections Page,
                     'assignments' Course Assignments List, 'syllabus' Course Syllabus Page
        syllabus_body: The syllabus body for the course
        syllabus_course_summary: Indicates whether the Course Summary (consisting of the course's assignments 
                                and calendar events) is displayed on the syllabus page. Defaults to true
        grading_standard_id: The grading standard id to set for the course. If no value is provided 
                            for this argument the current grading_standard will be un-set from this course
        grade_passback_setting: Optional. The grade_passback_setting for the course. Only 'nightly_sync' 
                               and empty string are allowed
        course_format: Optional. Specifies the format of the course. Should be either 'on_campus' or 'online'
        image_id: This is a file ID corresponding to an image file in the course that will be used as 
                 the course image. This will clear the course's image_url setting if set. If you attempt 
                 to provide image_url and image_id in a request it will fail
        image_url: This is a URL to an image to be used as the course image. This will clear the course's 
                  image_id setting if set. If you attempt to provide image_url and image_id in a request it will fail
        remove_image: If this option is set to true, the course image url and course image ID are both set to nil
        remove_banner_image: If this option is set to true, the course banner image url and course banner 
                            image ID are both set to nil
        blueprint: Sets the course as a blueprint course
        blueprint_restrictions: Sets a default set to apply to blueprint course objects when restricted, 
                               unless use_blueprint_restrictions_by_object_type is enabled
        use_blueprint_restrictions_by_object_type: When enabled, the blueprint_restrictions parameter will 
                                                  be ignored in favor of the blueprint_restrictions_by_object_type parameter
        blueprint_restrictions_by_object_type: Allows setting multiple Blueprint Restriction to apply to 
                                              blueprint course objects of the matching type when restricted. 
                                              The possible object types are "assignment", "attachment", 
                                              "discussion_topic", "quiz" and "wiki_page"
        homeroom_course: Sets the course as a homeroom course. The setting takes effect only when the course 
                        is associated with a Canvas for Elementary-enabled account
        sync_enrollments_from_homeroom: Syncs enrollments from the homeroom that is set in homeroom_course_id. 
                                       The setting only takes effect when the course is associated with a Canvas for 
                                       Elementary-enabled account and sync_enrollments_from_homeroom is enabled
        homeroom_course_id: Sets the Homeroom Course id to be used with sync_enrollments_from_homeroom. 
                           The setting only takes effect when the course is associated with a Canvas for Elementary-enabled 
                           account and sync_enrollments_from_homeroom is enabled
        template: Enable or disable the course as a template that can be selected by an account
        course_color: Sets a color in hex code format to be associated with the course. The setting takes 
                     effect only when the course is associated with a Canvas for Elementary-enabled account
        friendly_name: Set a friendly name for the course. If this is provided and the course is associated 
                      with a Canvas for Elementary account, it will be shown instead of the course name. 
                      This setting takes priority over course nicknames defined by individual users
        enable_course_paces: Enable or disable Course Pacing for the course. This setting only has an effect 
                            when the Course Pacing feature flag is enabled for the sub-account. Otherwise, 
                            Course Pacing are always disabled
        conditional_release: Enable or disable individual learning paths for students based on assessment
        post_manually: When true, all grades in the course will be posted manually. When false, all grades 
                      in the course will be automatically posted. Use with caution as this setting will 
                      override any assignment level post policy
        offer: If this option is set to true, the course will be available to students immediately
        override_sis_stickiness: Default is true. If false, any fields containing "sticky" changes will not 
                                be updated. See SIS CSV Format documentation for information on which fields 
                                can have SIS stickiness

    Returns:
        Updated Course dictionary

    Raises:
        ValueError: If validation fails for license, default_view, course_format, event, or other parameters

    Note:
        Arguments are the same as create_course, with a few exceptions (enroll_me).
        If a user has content management rights, but not full course editing rights, the only attribute 
        editable through this endpoint will be "syllabus_body".
        If an account has set prevent_course_availability_editing_by_teachers, a teacher cannot change 
        start_at, end_at, or restrict_enrollments_to_course_dates here.
    """
    # Validate license
    if license is not None:
        valid_licenses = {
            "private",
            "cc_by_nc_nd",
            "cc_by_nc_sa",
            "cc_by_nc",
            "cc_by_nd",
            "cc_by_sa",
            "cc_by",
            "public_domain",
        }
        if license not in valid_licenses:
            raise ValueError(
                f"Invalid license '{license}'. "
                f"Allowed values: {', '.join(sorted(valid_licenses))}"
            )

    # Validate default_view
    if default_view is not None:
        valid_default_views = {"feed", "wiki", "modules", "syllabus", "assignments"}
        if default_view not in valid_default_views:
            raise ValueError(
                f"Invalid default_view '{default_view}'. "
                f"Allowed values: {', '.join(sorted(valid_default_views))}"
            )

    # Validate course_format
    if course_format is not None:
        valid_course_formats = {"on_campus", "online"}
        if course_format not in valid_course_formats:
            raise ValueError(
                f"Invalid course_format '{course_format}'. "
                f"Allowed values: {', '.join(sorted(valid_course_formats))}"
            )

    # Validate event
    if event is not None:
        valid_events = {"claim", "offer", "conclude", "delete", "undelete"}
        if event not in valid_events:
            raise ValueError(
                f"Invalid event '{event}'. "
                f"Allowed values: {', '.join(sorted(valid_events))}"
            )

    # Validate storage_quota_mb
    if storage_quota_mb is not None and storage_quota_mb < 0:
        raise ValueError("storage_quota_mb must be non-negative")

    # Validate grading_standard_id
    if grading_standard_id is not None and grading_standard_id < 0:
        raise ValueError("grading_standard_id must be non-negative")

    # Validate image conflicts
    if image_id is not None and image_url is not None:
        raise ValueError("Cannot provide both image_id and image_url in the same request")

    # Validate account_id
    if account_id is not None and account_id < 0:
        raise ValueError("account_id must be non-negative")

    # Validate course_color format (if provided, should be hex color)
    if course_color is not None:
        if not course_color.startswith('#') or len(course_color) != 7:
            raise ValueError("course_color must be in hex format (e.g., '#FF5733')")
        try:
            int(course_color[1:], 16)
        except ValueError:
            raise ValueError("course_color must be a valid hex color code")

    data = {}

    # Add all course parameters
    if account_id is not None:
        data["course[account_id]"] = account_id
    if name is not None:
        data["course[name]"] = name
    if course_code is not None:
        data["course[course_code]"] = course_code
    if start_at is not None:
        data["course[start_at]"] = start_at
    if end_at is not None:
        data["course[end_at]"] = end_at
    if license is not None:
        data["course[license]"] = license
    if is_public is not None:
        data["course[is_public]"] = is_public
    if is_public_to_auth_users is not None:
        data["course[is_public_to_auth_users]"] = is_public_to_auth_users
    if public_syllabus is not None:
        data["course[public_syllabus]"] = public_syllabus
    if public_syllabus_to_auth is not None:
        data["course[public_syllabus_to_auth]"] = public_syllabus_to_auth
    if public_description is not None:
        data["course[public_description]"] = public_description
    if allow_student_wiki_edits is not None:
        data["course[allow_student_wiki_edits]"] = allow_student_wiki_edits
    if allow_wiki_comments is not None:
        data["course[allow_wiki_comments]"] = allow_wiki_comments
    if allow_student_forum_attachments is not None:
        data["course[allow_student_forum_attachments]"] = allow_student_forum_attachments
    if open_enrollment is not None:
        data["course[open_enrollment]"] = open_enrollment
    if self_enrollment is not None:
        data["course[self_enrollment]"] = self_enrollment
    if restrict_enrollments_to_course_dates is not None:
        data["course[restrict_enrollments_to_course_dates]"] = restrict_enrollments_to_course_dates
    if term_id is not None:
        data["course[term_id]"] = term_id
    if sis_course_id is not None:
        data["course[sis_course_id]"] = sis_course_id
    if integration_id is not None:
        data["course[integration_id]"] = integration_id
    if hide_final_grades is not None:
        data["course[hide_final_grades]"] = hide_final_grades
    if time_zone is not None:
        data["course[time_zone]"] = time_zone
    if apply_assignment_group_weights is not None:
        data["course[apply_assignment_group_weights]"] = apply_assignment_group_weights
    if storage_quota_mb is not None:
        data["course[storage_quota_mb]"] = storage_quota_mb
    if event is not None:
        data["course[event]"] = event
    if default_view is not None:
        data["course[default_view]"] = default_view
    if syllabus_body is not None:
        data["course[syllabus_body]"] = syllabus_body
    if syllabus_course_summary is not None:
        data["course[syllabus_course_summary]"] = syllabus_course_summary
    if grading_standard_id is not None:
        data["course[grading_standard_id]"] = grading_standard_id
    if grade_passback_setting is not None:
        data["course[grade_passback_setting]"] = grade_passback_setting
    if course_format is not None:
        data["course[course_format]"] = course_format
    if image_id is not None:
        data["course[image_id]"] = image_id
    if image_url is not None:
        data["course[image_url]"] = image_url
    if remove_image is not None:
        data["course[remove_image]"] = remove_image
    if remove_banner_image is not None:
        data["course[remove_banner_image]"] = remove_banner_image
    if blueprint is not None:
        data["course[blueprint]"] = blueprint
    if blueprint_restrictions is not None:
        data["course[blueprint_restrictions]"] = blueprint_restrictions
    if use_blueprint_restrictions_by_object_type is not None:
        data["course[use_blueprint_restrictions_by_object_type]"] = use_blueprint_restrictions_by_object_type
    if blueprint_restrictions_by_object_type is not None:
        data["course[blueprint_restrictions_by_object_type]"] = blueprint_restrictions_by_object_type
    if homeroom_course is not None:
        data["course[homeroom_course]"] = homeroom_course
    if sync_enrollments_from_homeroom is not None:
        data["course[sync_enrollments_from_homeroom]"] = sync_enrollments_from_homeroom
    if homeroom_course_id is not None:
        data["course[homeroom_course_id]"] = homeroom_course_id
    if template is not None:
        data["course[template]"] = template
    if course_color is not None:
        data["course[course_color]"] = course_color
    if friendly_name is not None:
        data["course[friendly_name]"] = friendly_name
    if enable_course_paces is not None:
        data["course[enable_course_paces]"] = enable_course_paces
    if conditional_release is not None:
        data["course[conditional_release]"] = conditional_release
    if post_manually is not None:
        data["course[post_manually]"] = post_manually

    if offer is not None:
        data["offer"] = offer
    if override_sis_stickiness is not None:
        data["override_sis_stickiness"] = override_sis_stickiness

    response = _make_request(
        base_url, access_token, "PUT", f"/api/v1/courses/{course_id}", data=data
    )
    return response.json()


def delete_conclude_course(
    base_url: str, access_token: str, course_id: Union[int, str], event: str
) -> Dict:
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
    response = _make_request(
        base_url, access_token, "DELETE", f"/api/v1/courses/{course_id}", data=data
    )
    return response.json()


def batch_update_courses(
    base_url: str,
    access_token: str,
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
        base_url,
        access_token,
        "PUT",
        f"/api/v1/accounts/{account_id}/courses",
        data=data,
    )
    return response.json()


def reset_course_content(
    base_url: str, access_token: str, course_id: Union[int, str]
) -> Dict:
    """
    Reset course content (deletes current course and creates new equivalent).

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        New course dictionary
    """
    response = _make_request(
        base_url, access_token, "POST", f"/api/v1/courses/{course_id}/reset_content"
    )
    return response.json()


# Course Users Methods


def list_course_users(
    base_url: str,
    access_token: str,
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
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/users",
            params=params,
        )
    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/users",
            params=params,
        )
        return response.json()


def get_course_user(
    base_url: str,
    access_token: str,
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
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/users/{user_id}",
        params=params,
    )
    return response.json()


def list_students(
    base_url: str,
    access_token: str,
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
        return _get_all_pages(
            base_url, access_token, "GET", f"/api/v1/courses/{course_id}/students"
        )
    else:
        response = _make_request(
            base_url, access_token, "GET", f"/api/v1/courses/{course_id}/students"
        )
        return response.json()


def list_recent_students(
    base_url: str,
    access_token: str,
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
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/recent_students",
        )
    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/recent_students",
        )
        return response.json()


def search_content_share_users(
    base_url: str,
    access_token: str,
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
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/content_share_users",
            data=data,
        )
    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/content_share_users",
            data=data,
        )
        return response.json()


# Course Progress Methods


def get_user_progress(
    base_url: str,
    access_token: str,
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
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/users/{user_id}/progress",
    )
    return response.json()


def get_bulk_user_progress(
    base_url: str, access_token: str, course_id: Union[int, str]
) -> List[Dict]:
    """
    Get progress for all users in course.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        List of user progress dictionaries
    """
    response = _make_request(
        base_url, access_token, "GET", f"/api/v1/courses/{course_id}/bulk_user_progress"
    )
    return response.json()


# Course Settings Methods


def get_course_settings(
    base_url: str, access_token: str, course_id: Union[int, str]
) -> Dict:
    """
    Get course settings.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        Course settings dictionary
    """
    response = _make_request(
        base_url, access_token, "GET", f"/api/v1/courses/{course_id}/settings"
    )
    return response.json()


def update_course_settings(
    base_url: str, access_token: str, course_id: Union[int, str], settings: Dict
) -> Dict:
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
        base_url,
        access_token,
        "PUT",
        f"/api/v1/courses/{course_id}/settings",
        data=settings,
    )
    return response.json()


# Course Activity Methods


def get_activity_stream(
    base_url: str,
    access_token: str,
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
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/activity_stream",
        )
    else:
        response = _make_request(
            base_url,
            access_token,
            "GET",
            f"/api/v1/courses/{course_id}/activity_stream",
        )
        return response.json()


def get_activity_stream_summary(
    base_url: str, access_token: str, course_id: Union[int, str]
) -> Dict:
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
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/activity_stream/summary",
    )
    return response.json()


def get_todo_items(
    base_url: str, access_token: str, course_id: Union[int, str]
) -> List[Dict]:
    """
    Get course TODO items for current user.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        course_id: Course ID

    Returns:
        List of TODO items
    """
    response = _make_request(
        base_url, access_token, "GET", f"/api/v1/courses/{course_id}/todo"
    )
    return response.json()


# Utility Methods


def preview_html(
    base_url: str, access_token: str, course_id: Union[int, str], html: str
) -> Dict:
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
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/preview_html",
        data=data,
    )
    return response.json()


def upload_file(
    base_url: str, access_token: str, course_id: Union[int, str], **kwargs
) -> Dict:
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
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/files",
        data=kwargs,
    )
    return response.json()


def get_student_view_student(
    base_url: str, access_token: str, course_id: Union[int, str]
) -> Dict:
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
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/student_view_student",
    )
    return response.json()


def get_effective_due_dates(
    base_url: str,
    access_token: str,
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
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/effective_due_dates",
        params=params,
    )
    return response.json()


def get_permissions(
    base_url: str, access_token: str, course_id: Union[int, str], permissions: List[str]
) -> Dict:
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
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/permissions",
        data=data,
    )
    return response.json()


def dismiss_migration_alert(
    base_url: str, access_token: str, course_id: Union[int, str]
) -> Dict:
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
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/dismiss_migration_limitation_message",
    )
    return response.json()


# Course Copy Methods (DEPRECATED)


def get_course_copy_status(
    base_url: str,
    access_token: str,
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
        base_url,
        access_token,
        "GET",
        f"/api/v1/courses/{course_id}/course_copy/{copy_id}",
    )
    return response.json()


def copy_course_content(
    base_url: str,
    access_token: str,
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
        base_url,
        access_token,
        "POST",
        f"/api/v1/courses/{course_id}/course_copy",
        data=data,
    )
    return response.json()
