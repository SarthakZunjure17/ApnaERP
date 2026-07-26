from typing import Generic, TypeVar
from app.repositories.base import BaseRepository

RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService(Generic[RepoType]):
    """
    Abstract Base Service enforcing Clean Architecture service layer contract.
    Encapsulates domain logic and delegates data persistence to Repositories.
    """
    def __init__(self, repository: RepoType):
        self.repository = repository
