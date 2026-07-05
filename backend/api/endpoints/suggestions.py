from fastapi import APIRouter

from backend.models.schemas import SuggestionQuestion

router = APIRouter()


@router.get("/api/v1/suggestions", response_model=list[SuggestionQuestion])
async def get_suggestions():
    return [
        SuggestionQuestion(text="Can I claim my laptop on tax?", category="ATO"),
        SuggestionQuestion(
            text="How do I apply for JobSeeker?", category="Centrelink"
        ),
        SuggestionQuestion(
            text="What is the shortcut method for working from home?",
            category="ATO",
        ),
        SuggestionQuestion(
            text="How do I replace my Medicare card?", category="Medicare"
        ),
        SuggestionQuestion(
            text="Who qualifies for the Low Income Health Care Card?",
            category="Centrelink",
        ),
    ]
