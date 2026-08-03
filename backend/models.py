from typing import List
from pydantic import BaseModel, Field

class ContentIdea(BaseModel):
    topic: str = Field(description="Main topic of the short or video")
    hook: str = Field(description="Hook style like curiosity, shock, controversy, etc")
    quote: str = Field(description="Powerful or viral quote used in the content")
    why: str = Field(description="Why this idea or quote will work")

class ContentIdeasList(BaseModel):
    contentList: List[ContentIdea]

class ShortScript(BaseModel):
    final_short_text: str = Field(
        ...,
        description="Full final narration text for the short"
    )
    phrases: List[str] = Field(
        ...,
        min_length=1,
        description="Sequential phrases split from the final_short_text for timing and subtitle alignment"
    )



class ShortsList(BaseModel):
    shorts: List[ShortScript]



from pydantic import BaseModel, Field
from typing import List


class ShortContent(BaseModel):
    topic: str = Field(
        description=(
            "Short hook-style title derived ONLY from the quote. "
            "Must not introduce new ideas or claims."
        )
    )

    virality_score: int = Field(
        description=(
            "Virality score from 1 to 10 based only on emotional intensity "
            "and clarity explicitly present in the quote."
        )
    )

    reason: str = Field(
        description=(
            "Literal reason why this quote works as a short. "
            "Must reference only what is explicitly stated in the quote. "
            "No inference or interpretation."
        )
    )

    quote: str = Field(
        description=(
            "Exact verbatim text copied from the script. "
            "Must be a single continuous span. "
            "No paraphrasing, no ellipses, no added or missing words."
        )
    )

    content_category:str

class ShortsExtractionResult(BaseModel):
    contentList: List[ShortContent]


class ShortMetadata(BaseModel):
    title: str = Field(
        description=(
            "Catchy, concise YouTube Shorts title/hook (under 60 characters). "
            "Should be engaging and clickable."
        )
    )
    description: str = Field(
        description=(
            "YouTube Short description with relevant hashtags included. "
            "Should be 2-3 sentences with 3-5 hashtags at the end."
        )
    )
    tags: str = Field(
        description=(
            "Comma-separated tags for SEO and discoverability. "
            "5-10 relevant keywords, comma-separated, no hashtags."
        )
    ) 
