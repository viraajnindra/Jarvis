from tools.registry import REGISTRY, ToolSpec, execute_tool, tool, tool_schemas  # noqa: F401


def load_all() -> None:
    """Import tool modules so their @tool decorators register."""
    import tools.browser  # noqa: F401
    import tools.canvas  # noqa: F401
    import tools.comms  # noqa: F401
    import tools.research  # noqa: F401
    import tools.study  # noqa: F401
    import tools.system  # noqa: F401
    import tools.video  # noqa: F401
    import tools.web  # noqa: F401

    tools.canvas.init()
    tools.study.init()
