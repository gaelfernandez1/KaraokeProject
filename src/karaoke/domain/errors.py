class PipelineError(Exception):
    pass


class PreparationError(PipelineError):
    pass


class AudioSeparationError(PipelineError):
    pass


class AlignmentError(PipelineError):
    pass


class AlignmentTimeoutError(AlignmentError):
    pass


class RenderError(PipelineError):
    pass


class PersistenceError(PipelineError):
    pass


class JobCancelled(PipelineError):
    pass
