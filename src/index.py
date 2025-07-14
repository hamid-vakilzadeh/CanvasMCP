from fastmcp import FastMCP
from typing import Annotated, Literal
from datetime import datetime

from pydantic import Field

from canvasAPI.module import modules
from canvasAPI.course import courses
from canvasAPI.quiz import quizzes, quiz_questions


def validate_and_convert_params(**kwargs):
    """
    Validate and convert parameter values to their expected types using eval().
    """

    converted = {}

    for key, value in kwargs.items():
        if value is None:
            converted[key] = value
            continue

        # Keep non-strings as-is
        if not isinstance(value, str):
            converted[key] = value
            continue

        # Try to eval the string to convert it to proper type
        try:
            converted[key] = eval(value)
        except (SyntaxError, NameError, ValueError, TypeError):
            # If eval fails, keep as string
            converted[key] = value

    return converted


mcp = FastMCP(name="Canvas Assistant")


@mcp.tool(tags={"course"})
async def list_courses() -> list[dict]:
    """Get a list of all the courses the user has taught as a teacher.
    Use this function to get course information such as course name, course ID and term informaiton.
    """
    result = courses.list_courses(
        enrollment_type="teacher", include=["term"], all_pages=True
    )

    courses_list = [
        {
            "course_id": item["id"],
            "course_name": item["name"],
            "term_id": item["term"]["id"],
            "term_name": item["term"]["name"],
        }
        for item in result
    ]

    return courses_list


@mcp.tool(tags={"module"})
async def create_module(
    course_id: Annotated[
        str | int, Field(description="The course ID where the module should be added")
    ],
    name: Annotated[str, Field(description="The name of the module")],
    unlock_at: Annotated[
        datetime | None, Field(description="The date the module will unlock")
    ] = None,
    position: Annotated[
        int | str | None,
        Field(
            description="The position of this module in the course (1-based) in integer format."
        ),
    ] = None,
    require_sequential_progress: Annotated[
        bool | str | None,
        Field(description="Whether module items must be unlocked in order"),
    ] = None,
    prerequisite_module_ids: Annotated[
        list[int | str] | str | None,
        Field(
            description="IDs of Modules that must be completed before this one is unlocked. Prerequisite modules must precede this module (i.e. have a lower position value), otherwise they will be ignored"
        ),
    ] = None,
    publish_final_grade: Annotated[
        bool | str | None,
        Field(
            description="Whether to publish the student’s final grade for the course upon completion of this module.",
        ),
    ] = None,
) -> dict:
    """Create new Module in a course."""
    # Validate and convert parameters
    params = validate_and_convert_params(
        course_id=course_id,
        name=name,
        unlock_at=unlock_at,
        position=position,
        require_sequential_progress=require_sequential_progress,
        prerequisite_module_ids=prerequisite_module_ids,
        publish_final_grade=publish_final_grade,
    )

    return modules.create_module(**params)


@mcp.tool(tags={"module"})
async def list_modules(
    course_id: Annotated[
        str | int, Field(description="The course ID to list modules from")
    ],
    include: Annotated[
        list[Literal["items", "content_details"]] | str | None,
        Field(description="Additional data to include: 'items', 'content_details'"),
    ] = None,
    search_term: Annotated[
        str | None, Field(description="Partial name of modules to match")
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
) -> list[dict]:
    """List modules in a course."""
    params = validate_and_convert_params(
        course_id=course_id,
        include=include,
        search_term=search_term,
        student_id=student_id,
        all_pages=True,
    )
    return modules.list_modules(**params)


@mcp.tool(tags={"module"})
async def show_module(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID to show")],
    include: Annotated[
        list[Literal["items", "content_details"]] | str | None,
        Field(description="Additional data to include: 'items', 'content_details'"),
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
) -> dict:
    """Get information about a single module."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        include=include,
        student_id=student_id,
    )
    return modules.show_module(**params)


@mcp.tool(tags={"module"})
async def update_module(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID to update")],
    name: Annotated[str | None, Field(description="The name of the module")] = None,
    unlock_at: Annotated[
        datetime | None, Field(description="The date the module will unlock")
    ] = None,
    position: Annotated[
        int | str | None,
        Field(description="The position of this module in the course (1-based)"),
    ] = None,
    require_sequential_progress: Annotated[
        bool | str | None,
        Field(description="Whether module items must be unlocked in order"),
    ] = None,
    prerequisite_module_ids: Annotated[
        list[int | str] | str | None,
        Field(description="IDs of Modules that must be completed before this one"),
    ] = None,
    publish_final_grade: Annotated[
        bool | str | None,
        Field(description="Whether to publish final grade upon completion"),
    ] = None,
    published: Annotated[
        bool | str | None,
        Field(description="Whether module is published and visible to students"),
    ] = None,
) -> dict:
    """Update an existing module."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        name=name,
        unlock_at=unlock_at,
        position=position,
        require_sequential_progress=require_sequential_progress,
        prerequisite_module_ids=prerequisite_module_ids,
        publish_final_grade=publish_final_grade,
        published=published,
    )
    return modules.update_module(**params)


@mcp.tool(tags={"module"})
async def delete_module(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID to delete")],
) -> dict:
    """Delete a module."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
    )
    return modules.delete_module(**params)


@mcp.tool(tags={"module"})
async def relock_module(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID to relock")],
) -> dict:
    """Re-lock module progressions to reset them to default locked state."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
    )
    return modules.relock_module(**params)


@mcp.tool(tags={"module"})
async def list_module_items(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[
        str | int, Field(description="The module ID to list items from")
    ],
    include: Annotated[
        list[Literal["content_details"]] | str | None,
        Field(description="Additional data to include: 'content_details'"),
    ] = None,
    search_term: Annotated[
        str | None, Field(description="Partial title of items to match")
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
) -> list[dict]:
    """List items in a module."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        include=include,
        search_term=search_term,
        student_id=student_id,
        all_pages=True,
    )
    return modules.list_module_items(**params)


@mcp.tool(tags={"module"})
async def show_module_item(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID")],
    item_id: Annotated[str | int, Field(description="The module item ID to show")],
    include: Annotated[
        list[Literal["content_details"]] | str | None,
        Field(description="Additional data to include: 'content_details'"),
    ] = None,
    student_id: Annotated[
        str | int | None,
        Field(description="Returns module completion information for this student"),
    ] = None,
) -> dict:
    """Get information about a single module item."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        item_id=item_id,
        include=include,
        student_id=student_id,
    )
    return modules.show_module_item(**params)


@mcp.tool(tags={"module"})
async def create_module_item(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID to add item to")],
    item_type: Annotated[
        Literal[
            "File",
            "Page",
            "Discussion",
            "Assignment",
            "Quiz",
            "SubHeader",
            "ExternalUrl",
            "ExternalTool",
        ],
        Field(
            description="Type of content: File, Page, Discussion, Assignment, Quiz, SubHeader, ExternalUrl, ExternalTool"
        ),
    ],
    title: Annotated[str | None, Field(description="Name of the module item")] = None,
    content_id: Annotated[
        str | int | None,
        Field(
            description="ID of content to link (required except for ExternalUrl, Page, SubHeader)"
        ),
    ] = None,
    position: Annotated[
        int | str | None,
        Field(description="Position in module (1-based)"),
    ] = None,
    indent: Annotated[
        int | str | None,
        Field(description="0-based indent level"),
    ] = None,
    page_url: Annotated[
        str | None, Field(description="Wiki page URL suffix (required for Page type)")
    ] = None,
    external_url: Annotated[
        str | None,
        Field(description="External URL (required for ExternalUrl and ExternalTool)"),
    ] = None,
    new_tab: Annotated[
        bool | str | None,
        Field(description="Whether external tool opens in new tab (ExternalTool only)"),
    ] = None,
    completion_requirement_type: Annotated[
        Literal["must_view", "must_contribute", "must_submit", "must_mark_done"] | None,
        Field(
            description="Completion requirement: must_view, must_contribute, must_submit, must_mark_done"
        ),
    ] = None,
    completion_requirement_min_score: Annotated[
        int | str | None,
        Field(description="Min score for completion (min_score type only)"),
    ] = None,
    iframe_width: Annotated[
        int | str | None,
        Field(description="ExternalTool launch width"),
    ] = None,
    iframe_height: Annotated[
        int | str | None,
        Field(description="ExternalTool launch height"),
    ] = None,
) -> dict:
    """Create a new module item."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        item_type=item_type,
        title=title,
        content_id=content_id,
        position=position,
        indent=indent,
        page_url=page_url,
        external_url=external_url,
        new_tab=new_tab,
        completion_requirement_type=completion_requirement_type,
        completion_requirement_min_score=completion_requirement_min_score,
        iframe_width=iframe_width,
        iframe_height=iframe_height,
    )
    return modules.create_module_item(**params)


@mcp.tool(tags={"module"})
async def update_module_item(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID")],
    item_id: Annotated[str | int, Field(description="The module item ID to update")],
    title: Annotated[str | None, Field(description="Name of the module item")] = None,
    position: Annotated[
        int | str | None,
        Field(description="Position in module (1-based)"),
    ] = None,
    indent: Annotated[
        int | str | None,
        Field(description="0-based indent level"),
    ] = None,
    external_url: Annotated[
        str | None, Field(description="External URL (ExternalUrl type only)")
    ] = None,
    new_tab: Annotated[
        bool | str | None,
        Field(description="Whether external tool opens in new tab (ExternalTool only)"),
    ] = None,
    completion_requirement_type: Annotated[
        Literal["must_view", "must_contribute", "must_submit", "must_mark_done"] | None,
        Field(
            description="Completion requirement: must_view, must_contribute, must_submit, must_mark_done"
        ),
    ] = None,
    completion_requirement_min_score: Annotated[
        int | str | None,
        Field(description="Min score for completion (min_score type only)"),
    ] = None,
    published: Annotated[
        bool | str | None,
        Field(description="Whether item is published and visible to students"),
    ] = None,
    target_module_id: Annotated[
        str | int | None,
        Field(description="Move item to another module"),
    ] = None,
) -> dict:
    """Update an existing module item."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        item_id=item_id,
        title=title,
        position=position,
        indent=indent,
        external_url=external_url,
        new_tab=new_tab,
        completion_requirement_type=completion_requirement_type,
        completion_requirement_min_score=completion_requirement_min_score,
        published=published,
        target_module_id=target_module_id,
    )
    return modules.update_module_item(**params)


@mcp.tool(tags={"module"})
async def delete_module_item(
    course_id: Annotated[str | int, Field(description="The course ID")],
    module_id: Annotated[str | int, Field(description="The module ID")],
    item_id: Annotated[str | int, Field(description="The module item ID to delete")],
) -> dict:
    """Delete a module item."""
    params = validate_and_convert_params(
        course_id=course_id,
        module_id=module_id,
        item_id=item_id,
    )
    return modules.delete_module_item(**params)


# Quiz Management Tools


@mcp.tool(tags={"quiz"})
async def list_quizzes(
    course_id: Annotated[
        str | int, Field(description="The course ID to list quizzes from")
    ],
    search_term: Annotated[
        str | None,
        Field(description="The partial title of the quizzes to match and return"),
    ] = None,
) -> list[dict]:
    """List quizzes in a course."""
    params = validate_and_convert_params(
        course_id=course_id,
        search_term=search_term,
        all_pages=True,
    )
    return quizzes.list_quizzes(**params)


@mcp.tool(tags={"quiz"})
async def get_quiz(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID to get")],
) -> dict:
    """Get a single quiz."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
    )
    return quizzes.get_quiz(**params)


@mcp.tool(tags={"quiz"})
async def create_quiz(
    course_id: Annotated[str | int, Field(description="The course ID")],
    title: Annotated[str, Field(description="The quiz title")],
    description: Annotated[
        str | None, Field(description="A description of the quiz")
    ] = None,
    quiz_type: Annotated[
        Literal["practice_quiz", "assignment", "graded_survey", "survey"] | None,
        Field(description="The type of quiz"),
    ] = "assignment",
    assignment_group_id: Annotated[
        int | str | None,
        Field(description="The assignment group id to put the assignment in"),
    ] = None,
    time_limit: Annotated[
        int | str | None, Field(description="Time limit to take this quiz, in minutes")
    ] = None,
    shuffle_answers: Annotated[
        bool | str | None,
        Field(
            description="If true, quiz answers for multiple choice questions will be randomized"
        ),
    ] = False,
    hide_results: Annotated[
        Literal["always", "until_after_last_attempt"] | None,
        Field(description="Dictates whether quiz results are hidden from students"),
    ] = None,
    show_correct_answers: Annotated[
        bool | str | None,
        Field(description="If false, hides correct answers from students"),
    ] = True,
    show_correct_answers_last_attempt: Annotated[
        bool | str | None, Field(description="Hides correct answers until last attempt")
    ] = False,
    allowed_attempts: Annotated[
        int | str | None,
        Field(description="Number of times a student is allowed to take a quiz"),
    ] = 1,
    scoring_policy: Annotated[
        Literal["keep_highest", "keep_latest"] | None,
        Field(description="Scoring policy for multiple attempts"),
    ] = "keep_highest",
    one_question_at_a_time: Annotated[
        bool | str | None,
        Field(description="If true, shows quiz to student one question at a time"),
    ] = False,
    cant_go_back: Annotated[
        bool | str | None,
        Field(description="If true, questions are locked after answering"),
    ] = False,
    access_code: Annotated[
        str | None, Field(description="Restricts access to the quiz with a password")
    ] = None,
    ip_filter: Annotated[
        str | None,
        Field(
            description="Restricts access to the quiz to computers in a specified IP range"
        ),
    ] = None,
    published: Annotated[
        bool | str | None,
        Field(description="Whether the quiz should be published or unpublished"),
    ] = True,
    one_time_results: Annotated[
        bool | str | None,
        Field(
            description="Whether students should be prevented from viewing results past first time"
        ),
    ] = False,
    only_visible_to_overrides: Annotated[
        bool | str | None,
        Field(description="Whether this quiz is only visible to overrides"),
    ] = False,
) -> dict:
    """Create a new quiz for this course."""
    params = validate_and_convert_params(
        course_id=course_id,
        title=title,
        description=description,
        quiz_type=quiz_type,
        assignment_group_id=assignment_group_id,
        time_limit=time_limit,
        shuffle_answers=shuffle_answers,
        hide_results=hide_results,
        show_correct_answers=show_correct_answers,
        show_correct_answers_last_attempt=show_correct_answers_last_attempt,
        allowed_attempts=allowed_attempts,
        scoring_policy=scoring_policy,
        one_question_at_a_time=one_question_at_a_time,
        cant_go_back=cant_go_back,
        access_code=access_code,
        ip_filter=ip_filter,
        published=published,
        one_time_results=one_time_results,
        only_visible_to_overrides=only_visible_to_overrides,
    )
    return quizzes.create_quiz(**params)


@mcp.tool(tags={"quiz"})
async def update_quiz(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID to update")],
    title: Annotated[str | None, Field(description="The quiz title")] = None,
    description: Annotated[
        str | None, Field(description="A description of the quiz")
    ] = None,
    quiz_type: Annotated[
        Literal["practice_quiz", "assignment", "graded_survey", "survey"] | None,
        Field(description="The type of quiz"),
    ] = None,
    assignment_group_id: Annotated[
        int | str | None,
        Field(description="The assignment group id to put the assignment in"),
    ] = None,
    time_limit: Annotated[
        int | str | None, Field(description="Time limit to take this quiz, in minutes")
    ] = None,
    shuffle_answers: Annotated[
        bool | str | None,
        Field(
            description="If true, quiz answers for multiple choice questions will be randomized"
        ),
    ] = None,
    hide_results: Annotated[
        Literal["always", "until_after_last_attempt"] | None,
        Field(description="Dictates whether quiz results are hidden from students"),
    ] = None,
    show_correct_answers: Annotated[
        bool | str | None,
        Field(description="If false, hides correct answers from students"),
    ] = None,
    show_correct_answers_last_attempt: Annotated[
        bool | str | None, Field(description="Hides correct answers until last attempt")
    ] = None,
    allowed_attempts: Annotated[
        int | str | None,
        Field(description="Number of times a student is allowed to take a quiz"),
    ] = None,
    scoring_policy: Annotated[
        Literal["keep_highest", "keep_latest"] | None,
        Field(description="Scoring policy for multiple attempts"),
    ] = None,
    one_question_at_a_time: Annotated[
        bool | str | None,
        Field(description="If true, shows quiz to student one question at a time"),
    ] = None,
    cant_go_back: Annotated[
        bool | str | None,
        Field(description="If true, questions are locked after answering"),
    ] = None,
    access_code: Annotated[
        str | None, Field(description="Restricts access to the quiz with a password")
    ] = None,
    ip_filter: Annotated[
        str | None,
        Field(
            description="Restricts access to the quiz to computers in a specified IP range"
        ),
    ] = None,
    published: Annotated[
        bool | str | None,
        Field(description="Whether the quiz should be published or unpublished"),
    ] = None,
    one_time_results: Annotated[
        bool | str | None,
        Field(
            description="Whether students should be prevented from viewing results past first time"
        ),
    ] = None,
    only_visible_to_overrides: Annotated[
        bool | str | None,
        Field(description="Whether this quiz is only visible to overrides"),
    ] = None,
    notify_of_update: Annotated[
        bool | str | None,
        Field(description="If true, notifies users that the quiz has changed"),
    ] = True,
) -> dict:
    """Update an existing quiz."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
        title=title,
        description=description,
        quiz_type=quiz_type,
        assignment_group_id=assignment_group_id,
        time_limit=time_limit,
        shuffle_answers=shuffle_answers,
        hide_results=hide_results,
        show_correct_answers=show_correct_answers,
        show_correct_answers_last_attempt=show_correct_answers_last_attempt,
        allowed_attempts=allowed_attempts,
        scoring_policy=scoring_policy,
        one_question_at_a_time=one_question_at_a_time,
        cant_go_back=cant_go_back,
        access_code=access_code,
        ip_filter=ip_filter,
        published=published,
        one_time_results=one_time_results,
        only_visible_to_overrides=only_visible_to_overrides,
        notify_of_update=notify_of_update,
    )
    return quizzes.update_quiz(**params)


@mcp.tool(tags={"quiz"})
async def delete_quiz(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID to delete")],
) -> dict:
    """Delete a quiz."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
    )
    return quizzes.delete_quiz(**params)


@mcp.tool(tags={"quiz"})
async def validate_quiz_access_code(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID")],
    access_code: Annotated[str, Field(description="The access code being validated")],
) -> dict:
    """Validate quiz access code."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
        access_code=access_code,
    )
    return quizzes.validate_access_code(**params)


# Quiz Question Management Tools


@mcp.tool(tags={"quiz", "question"})
async def list_quiz_questions(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID")],
    quiz_submission_id: Annotated[
        int | str | None,
        Field(description="If specified, return questions for that submission"),
    ] = None,
    quiz_submission_attempt: Annotated[
        int | str | None,
        Field(description="The attempt of the submission you want questions for"),
    ] = None,
) -> list[dict]:
    """List questions in a quiz or a submission."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
        quiz_submission_id=quiz_submission_id,
        quiz_submission_attempt=quiz_submission_attempt,
        all_pages=True,
    )
    return quiz_questions.list_quiz_questions(**params)


@mcp.tool(tags={"quiz", "question"})
async def get_quiz_question(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID")],
    question_id: Annotated[str | int, Field(description="The question ID")],
) -> dict:
    """Get a single quiz question."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
        question_id=question_id,
    )
    return quiz_questions.get_quiz_question(**params)


@mcp.tool(tags={"quiz", "question"})
async def create_quiz_question(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID")],
    question_name: Annotated[
        str | None, Field(description="The name of the question")
    ] = None,
    question_text: Annotated[
        str | None, Field(description="The text of the question")
    ] = None,
    question_type: Annotated[
        Literal[
            "calculated_question",
            "essay_question",
            "file_upload_question",
            "fill_in_multiple_blanks_question",
            "matching_question",
            "multiple_answers_question",
            "multiple_choice_question",
            "multiple_dropdowns_question",
            "numerical_question",
            "short_answer_question",
            "text_only_question",
            "true_false_question",
        ]
        | None,
        Field(description="The type of question"),
    ] = None,
    position: Annotated[
        int | str | None,
        Field(description="The order in which the question will be displayed"),
    ] = None,
    points_possible: Annotated[
        int | str | None,
        Field(
            description="The maximum amount of points received for answering correctly"
        ),
    ] = None,
    correct_comments: Annotated[
        str | None,
        Field(description="The comment to display if the student answers correctly"),
    ] = None,
    incorrect_comments: Annotated[
        str | None,
        Field(description="The comment to display if the student answers incorrectly"),
    ] = None,
    neutral_comments: Annotated[
        str | None,
        Field(
            description="The comment to display regardless of how the student answered"
        ),
    ] = None,
    text_after_answers: Annotated[
        str | None,
        Field(description="Text to follow answers (used in missing word questions)"),
    ] = None,
    quiz_group_id: Annotated[
        int | str | None,
        Field(description="The id of the quiz group to assign the question to"),
    ] = None,
    answers: Annotated[
        list[dict] | str | None,
        Field(description="The answers"),
    ] = None,
) -> dict:
    """Create a new quiz question for this quiz."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
        question_name=question_name,
        question_text=question_text,
        question_type=question_type,
        position=position,
        points_possible=points_possible,
        correct_comments=correct_comments,
        incorrect_comments=incorrect_comments,
        neutral_comments=neutral_comments,
        text_after_answers=text_after_answers,
        quiz_group_id=quiz_group_id,
        answers=answers,
    )
    return quiz_questions.create_quiz_question(**params)


@mcp.tool(tags={"quiz", "question"})
async def update_quiz_question(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID")],
    question_id: Annotated[str | int, Field(description="The question ID")],
    question_name: Annotated[
        str | None, Field(description="The name of the question")
    ] = None,
    question_text: Annotated[
        str | None, Field(description="The text of the question")
    ] = None,
    question_type: Annotated[
        Literal[
            "calculated_question",
            "essay_question",
            "file_upload_question",
            "fill_in_multiple_blanks_question",
            "matching_question",
            "multiple_answers_question",
            "multiple_choice_question",
            "multiple_dropdowns_question",
            "numerical_question",
            "short_answer_question",
            "text_only_question",
            "true_false_question",
        ]
        | None,
        Field(description="The type of question"),
    ] = None,
    position: Annotated[
        int | str | None,
        Field(description="The order in which the question will be displayed"),
    ] = None,
    points_possible: Annotated[
        int | str | None,
        Field(
            description="The maximum amount of points received for answering correctly"
        ),
    ] = None,
    correct_comments: Annotated[
        str | None,
        Field(description="The comment to display if the student answers correctly"),
    ] = None,
    incorrect_comments: Annotated[
        str | None,
        Field(description="The comment to display if the student answers incorrectly"),
    ] = None,
    neutral_comments: Annotated[
        str | None,
        Field(
            description="The comment to display regardless of how the student answered"
        ),
    ] = None,
    text_after_answers: Annotated[
        str | None,
        Field(description="Text to follow answers (used in missing word questions)"),
    ] = None,
    quiz_group_id: Annotated[
        int | str | None,
        Field(description="The id of the quiz group to assign the question to"),
    ] = None,
    answers: Annotated[
        list[dict] | str | None,
        Field(description="The answers"),
    ] = None,
) -> dict:
    """Update an existing quiz question for this quiz."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
        question_id=question_id,
        question_name=question_name,
        question_text=question_text,
        question_type=question_type,
        position=position,
        points_possible=points_possible,
        correct_comments=correct_comments,
        incorrect_comments=incorrect_comments,
        neutral_comments=neutral_comments,
        text_after_answers=text_after_answers,
        quiz_group_id=quiz_group_id,
        answers=answers,
    )
    return quiz_questions.update_quiz_question(**params)


@mcp.tool(tags={"quiz", "question"})
async def delete_quiz_question(
    course_id: Annotated[str | int, Field(description="The course ID")],
    quiz_id: Annotated[str | int, Field(description="The quiz ID")],
    question_id: Annotated[str | int, Field(description="The question ID")],
) -> dict:
    """Delete a quiz question."""
    params = validate_and_convert_params(
        course_id=course_id,
        quiz_id=quiz_id,
        question_id=question_id,
    )
    quiz_questions.delete_quiz_question(**params)
    return {"success": True, "message": "Question deleted successfully"}


if __name__ == "__main__":
    mcp.run()
