from pydantic import BaseModel
from typing import List


class AvailableLabelResponse(BaseModel):
    available_labels: List[int]