import enum
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, object_session, relationship

from tour_guide_bot import t
from tour_guide_bot.helpers.currency import Currency
from tour_guide_bot.models import Base
from tour_guide_bot.models.settings import PaymentProvider


class Tour(Base):
    __tablename__ = "tour"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    translations: Mapped[list["TourTranslation"]] = relationship(
        "TourTranslation",
        back_populates="tour",
        cascade="all, delete-orphan",
        order_by="TourTranslation.id",
    )
    purchases: Mapped[list["Subscription"]] = relationship(
        "Subscription", cascade="all, delete-orphan", back_populates="tour"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", cascade="all, delete-orphan", back_populates="tour"
    )
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="tour",
        cascade="all, delete-orphan",
        order_by="Product.currency, Product.price",
    )
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    def sections(self, language):
        return (
            object_session(self)
            .query(TourSection)
            .with_parent(TourTranslation)
            .filter(TourTranslation.language == language)
            .all
        )


class TourTranslation(Base):
    __tablename__ = "tour_translation"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    language: Mapped[str] = Column(String, nullable=False)
    tour_id: Mapped[int] = Column(Integer, ForeignKey("tour.id"), nullable=False)
    title: Mapped[str] = Column(String, nullable=False)
    description: Mapped[Optional[str]] = Column(String(4096), nullable=True)
    tour: Mapped[Optional["Tour"]] = relationship("Tour", back_populates="translations")
    sections: Mapped[list["TourSection"]] = relationship(
        "TourSection", cascade="all, delete-orphan", order_by="TourSection.position"
    )
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


class MessageType(enum.Enum):
    text = 1
    location = 2
    audio = 3
    voice = 4
    video = 5
    video_note = 6
    photo = 7
    media_group = 8
    animation = 9


class TourSection(Base):
    __tablename__ = "tour_section"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    tour_translation_id: Mapped[int] = Column(
        Integer, ForeignKey("tour_translation.id"), nullable=False
    )
    tour_translation: Mapped[list[TourTranslation]] = relationship(
        "TourTranslation", back_populates="sections"
    )
    title: Mapped[str] = Column(String, nullable=False)
    position: Mapped[int] = Column(SmallInteger, nullable=False)
    content: Mapped[list["TourSectionContent"]] = relationship(
        "TourSectionContent",
        cascade="all, delete-orphan",
        order_by="TourSectionContent.position",
    )
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "ix_tour_section_translation_id_position",
            "tour_translation_id",
            "position",
            unique=True,
        ),
    )


class TourSectionContent(Base):
    __tablename__ = "tour_section_content"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    tour_section_id: Mapped[int] = Column(
        Integer, ForeignKey("tour_section.id"), nullable=False
    )
    tour_section: Mapped[Optional["TourSection"]] = relationship(
        "TourSection", back_populates="content"
    )
    position: Mapped[int] = Column(SmallInteger, nullable=False)
    message_type: Mapped[MessageType] = Column(Enum(MessageType), nullable=False)
    media_group_id: Mapped[Optional[str]] = Column(String)
    content: Mapped[dict] = Column(MutableDict.as_mutable(JSON), nullable=False)
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "ix_tour_section_id_position", "tour_section_id", "position", unique=True
        ),
        Index(
            "ix_tour_section_content_secion_id_media_group",
            "tour_section_id",
            "message_type",
            "media_group_id",
            unique=True,
        ),
    )


class Product(Base):
    __tablename__ = "product"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    tour_id: Mapped[int] = Column(Integer, ForeignKey("tour.id"), nullable=False)
    tour: Mapped[Optional[Tour]] = relationship("Tour")
    payment_provider_id: Mapped[int] = Column(
        Integer, ForeignKey("payment_provider.id"), nullable=False
    )
    payment_provider: Mapped[Optional[PaymentProvider]] = relationship(PaymentProvider)
    currency: Mapped[str] = Column(String, nullable=False)
    price: Mapped[int] = Column(Integer, nullable=False)
    duration_days: Mapped[int] = Column(Integer, nullable=False)
    available: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    language: Mapped[str] = Column(String, nullable=False)
    title: Mapped[str] = Column(String(32), nullable=False)
    description: Mapped[str] = Column(String(255), nullable=False)
    guests: Mapped[int] = Column(Integer, nullable=False, default=1)
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "ix_product_language_tour",
            "language",
            "tour_id",
        ),
    )

    async def formatted_name(self, language: str) -> str:
        return (
            t(language)
            .npgettext(
                "tours",
                "{price} for {duration} day ({formatted_guests_count})",
                "{price} for {duration} days ({formatted_guests_count})",
                self.duration_days,
            )
            .format(
                price=await Currency.price_from_telegram(self.currency, self.price),
                duration=self.duration_days,
                formatted_guests_count=t(language)
                .npgettext(
                    "tours",
                    "for {guests_count} guest",
                    "for {guests_count} guests",
                    self.guests,
                )
                .format(guests_count=self.guests),
            )
        )


class Invoice(Base):
    __tablename__ = "invoice"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    product_id: Mapped[int] = Column(Integer, ForeignKey("product.id"), nullable=False)
    product: Mapped[Optional[Product]] = relationship("Product")
    tour_id: Mapped[int] = Column(Integer, ForeignKey("tour.id"), nullable=False)
    tour: Mapped[Optional[Tour]] = relationship("Tour")
    guest_id: Mapped[int] = Column(Integer, ForeignKey("guest.id"), nullable=False)
    guest: Mapped[Optional["Guest"]] = relationship("Guest")
    payment_provider_id: Mapped[int] = Column(
        Integer, ForeignKey("payment_provider.id"), nullable=False
    )
    payment_provider: Mapped[Optional[PaymentProvider]] = relationship(PaymentProvider)
    currency: Mapped[str] = Column(String, nullable=False)
    price: Mapped[int] = Column(Integer, nullable=False)
    duration_days: Mapped[int] = Column(Integer, nullable=False)
    guests: Mapped[int] = Column(Integer, nullable=False, default=1)
    paid: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="invoice"
    )
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


class Subscription(Base):
    __tablename__ = "subscription"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    guest_id: Mapped[int] = Column(
        Integer, ForeignKey("guest.id"), nullable=False, index=True
    )
    guest: Mapped[Optional["Guest"]] = relationship("Guest")
    tour_id: Mapped[int] = Column(Integer, ForeignKey("tour.id"), nullable=False)
    tour: Mapped[Optional["Tour"]] = relationship("Tour")
    is_user_notified: Mapped[bool] = Column(
        Boolean, nullable=False, default=False, index=True
    )
    invoice_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("invoice.id"), nullable=True
    )
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice")
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    expire_ts = Column(DateTime, nullable=False)


class Guest(Base):
    __tablename__ = "guest"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    phone: Mapped[str] = Column(String, index=True, unique=True, nullable=False)
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )


class TourDelivery(Base):
    """A tour section that is still being sent to a Telegram user.

    The row exists only while the section is being sent, so an interrupted send
    can be resumed after a restart.
    """

    __tablename__ = "tour_delivery"

    telegram_user_id: Mapped[int] = Column(
        BigInteger,
        ForeignKey("telegram_user.id"),
        primary_key=True,
        autoincrement=False,
    )
    chat_id: Mapped[int] = Column(BigInteger, nullable=False)
    tour_translation_id: Mapped[int] = Column(
        Integer, ForeignKey("tour_translation.id"), nullable=False, index=True
    )
    section_position: Mapped[int] = Column(SmallInteger, nullable=False)
    # TourSectionContent.position of the first part that wasn't sent yet
    next_content_position: Mapped[int] = Column(SmallInteger, nullable=False)
    # Identifies the send that owns the row: a newer send replaces it, and the
    # older one must not touch the row any more
    run_id: Mapped[str] = Column(String(32), nullable=False)
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(DateTime, nullable=False)
