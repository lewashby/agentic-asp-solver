

from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

def accumulate_stats(old_stats: dict, new_stats: dict) -> dict:
    return {
        key: old_stats.get(key, 0) + new_stats.get(key, 0)
        for key in set(old_stats) | set(new_stats)
    }

class ASPState(BaseModel):
    """State for the ASP multi-agent system"""
    
    # Original problem description from user
    problem_description: str = ""
    
    # Current ASP code being developed
    asp_code: str = ""

    # Chat history
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    
    # Validation feedback history
    validation_history: Annotated[list, add_messages] = Field(default_factory=list)
    
    # Current iteration count
    iteration_count: int = 0
    
    # Maximum iterations allowed
    max_iterations: int = 5
    
    # Validation status
    is_validated: bool = False

    # Test status
    is_tested: bool = False
    
    # Last validator feedback (for solver to see)
    last_feedback: str = ""

    # Answer set solution
    answer_set: str = ""

    # Usage statistics
    statistics: Annotated[dict, accumulate_stats] = { "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tool_calls": 0 }
    