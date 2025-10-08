

from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


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
    
    # Last validator feedback (for solver to see)
    last_feedback: str = ""
    
    # Error messages
    errors: Annotated[list, add_messages] = Field(default_factory=list)
    
    # Final status message
    status_message: str = ""
