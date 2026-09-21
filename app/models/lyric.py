from typing import List
from sqlalchemy import String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db
from app.utils.ids import generate_id

class LyricLine(db.Model):
    __tablename__ = "lyric_lines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_id("line"))
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, index=True)
    line_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[float] = mapped_column(Float, nullable=False)

    project = relationship("Project", back_populates="lyric_lines")
    words = relationship("LyricWord", back_populates="line", cascade="all, delete-orphan", order_by="LyricWord.word_index")

    def to_dict(self):
        return {
            "id": self.id,
            "line_index": self.line_index,
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "words": [w.to_dict() for w in self.words],
        }

class LyricWord(db.Model):
    __tablename__ = "lyric_words"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_id("word"))
    line_id: Mapped[str] = mapped_column(String(64), ForeignKey("lyric_lines.id", ondelete="CASCADE"), nullable=False, index=True)
    word_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    start: Mapped[float] = mapped_column(Float, nullable=False)
    end: Mapped[float] = mapped_column(Float, nullable=False)

    line = relationship("LyricLine", back_populates="words")

    def to_dict(self):
        return {
            "id": self.id,
            "word_index": self.word_index,
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
        }
