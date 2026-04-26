from rich.highlighter import RegexHighlighter


class DCSLogHighlighter(RegexHighlighter):
    """
    Highlighter for DCS log message content.
    Mirroring the rules from highlighter_dcs.js.
    """

    base_style = "log."
    highlights = [
        # URLs
        r"(?P<link>https?://[^\s]+)",
        # IPs
        r"\b(?P<link>(?:\d{1,3}\.){3}\d{1,3})\b",
        # Quoted Paths
        r"(?P<link>\"[a-zA-Z]:[\\/][^\"]+\")",
        r"(?P<link>'[a-zA-Z]:[\\/][^']+')",
        # Paths
        r"(?P<link>\b[a-zA-Z]:[\\/](?:[^:;*?\"<>|\r\n\t \[\]{}()]+|(?<=[\\/\w.-])\s+(?=[\w.-]+[\\/]))+)",
        # Brackets
        r"(?P<bracket>\[[^\]\r\n]+\])",
        # Braces
        r"(?P<brace>\{[^\}\r\n]+\})",
        # Member access
        r"\b(?P<member>[a-zA-Z0-9_]+::[a-zA-Z0-9_]+)\b",
        # Strings
        r"(?P<string>\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')",
    ]
