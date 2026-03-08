class UniversityClientError(Exception):
    pass


class UniversityAuthError(UniversityClientError):
    pass


class UniversityApiError(UniversityClientError):
    pass
