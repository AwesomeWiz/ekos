import html
from html.parser import HTMLParser
from typing import Any, List


class HTMLToTextParser(HTMLParser):
    """Simple, dependency-free HTML/XHTML parser that converts rich text to plain text.
    
    Preserves paragraph breaks, list bullets, and decoded entities while removing tags.
    """

    def __init__(self):
        super().__init__()
        self.result: List[str] = []
        self._skip = False
        self._in_pre = False

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        tag_lower = tag.lower()
        if tag_lower in {"script", "style"}:
            self._skip = True
        elif tag_lower == "pre":
            self._in_pre = True
            self.result.append("\n")
        elif tag_lower in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "div"}:
            self.result.append("\n")
        elif tag_lower == "br":
            self.result.append("\n")
        elif tag_lower == "li":
            self.result.append("\n- ")
        elif tag_lower in {"tr"}:
            self.result.append("\n")
        elif tag_lower in {"td", "th"}:
            self.result.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in {"script", "style"}:
            self._skip = False
        elif tag_lower == "pre":
            self._in_pre = False
            self.result.append("\n")
        elif tag_lower in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}:
            self.result.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data:
            self.result.append(data)

    def handle_entityref(self, name: str) -> None:
        if not self._skip:
            char = html.entities.name2codepoint.get(name)
            if char:
                self.result.append(chr(char))

    def handle_charref(self, name: str) -> None:
        if not self._skip:
            try:
                if name.startswith(("x", "X")):
                    char = chr(int(name[1:], 16))
                else:
                    char = chr(int(name))
                self.result.append(char)
            except ValueError:
                pass

    def get_text(self) -> str:
        raw = "".join(self.result)
        # Normalize line breaks and multiple consecutive empty lines
        lines = [line.strip() for line in raw.splitlines()]
        cleaned: List[str] = []
        last_empty = False
        for line in lines:
            if line:
                cleaned.append(line)
                last_empty = False
            elif not last_empty:
                cleaned.append("")
                last_empty = True
        return "\n".join(cleaned).strip()


def html_to_plain_text(content: Any) -> str:
    """Convert HTML or Confluence Storage Format XHTML to clean plain text.
    
    If content is empty or None, safely returns an empty string.
    """
    if not content:
        return ""
    if not isinstance(content, str):
        content = str(content)

    parser = HTMLToTextParser()
    try:
        parser.feed(content)
        parser.close()
        return parser.get_text()
    except Exception:
        # Fallback to unescaped string if parsing fails
        return html.unescape(content).strip()
