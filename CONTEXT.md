# Tour Guide Bot

A Telegram bot through which an Admin publishes virtual guided tours and Guests
walk through them, either after being approved by hand or after paying.

## Language

### People

**Guest**:
A person, identified by phone number, who may hold Subscriptions to Tours.
Exists independently of any Telegram account: an Admin can approve a phone
number before its owner ever opens the bot.
_Avoid_: user, customer, subscriber, visitor

**Admin**:
A person, identified by phone number, who manages tours, access and settings.
Admin rights are proven once by the bot token, after which the phone number is
trusted.
_Avoid_: owner, operator, manager

**Telegram User**:
A Telegram account that talks to the bot. Linked to at most one Guest and at
most one Admin; one Guest may be reached through several Telegram Users.
_Avoid_: user (on its own), account, chat

### Modes

**Guest Mode**:
The default way the bot behaves: it greets, asks for a phone number, lists the
Tours a Guest may take and walks them through one.
_Avoid_: guide mode, user mode, default mode

**Admin Mode**:
The state an Admin switches into to manage Tours, Products, Payment Providers,
access and messages. Left explicitly to return to Guest Mode.
_Avoid_: admin panel (that is the web interface), management mode

**Admin Panel**:
The optional web interface for Admins, entered through Telegram Login.
_Avoid_: admin mode, web admin, dashboard

### Tours

**Tour**:
A virtual guided tour. Language-neutral container for its Translations,
Products and Subscriptions; has no title of its own.
_Avoid_: excursion, route, course

**Tour Translation**:
One Tour in one language: a title, a description and an ordered list of
Sections. A Guest only ever sees the Translation for their language, falling
back to the Default Language.
_Avoid_: version, localisation, variant

**Section**:
One stop of a Tour Translation: a titled, ordered bundle of Content Items that
is delivered to the Guest as a batch when they move to it.
_Avoid_: step, stop, chapter, point, page

**Content Item**:
One Telegram message inside a Section: text, a location, a photo, a video, an
audio or voice clip, a video note, an animation or a media group.
_Avoid_: content (on its own), message, attachment, media

**Media Group**:
A Content Item made of several photos or videos sent together as one album.
_Avoid_: album, gallery

### Access

**Subscription**:
A Guest's time-bounded right to take one Tour. Created either by an Approval or
by a paid Invoice; extending an active one pushes its expiry further out
rather than creating a second one.
_Avoid_: purchase, bought tour, approved tour, access, grant, licence

**Approval**:
An Admin granting or extending a Subscription for a phone number for a given
number of days, with no payment involved.
_Avoid_: whitelisting, invite, manual purchase

**Revocation**:
An Admin ending a Guest's active Subscription immediately.
_Avoid_: ban, block, removal

**Availability Notice**:
The message telling a Guest that a new Subscription is waiting for them. Sent
once per Subscription.
_Avoid_: notification (on its own), alert

### Payments

**Product**:
A purchasable offer for one Tour in one language: a price in a currency, a
duration in days, a guest count, and the Payment Provider that will collect
the money. A Tour may have many Products; one may be switched off without
being deleted.
_Avoid_: price, pricing, plan, tariff, offer, SKU

**Guest Count**:
How many people a Product is meant to cover. Shown to the Guest as part of the
Product's name.
_Avoid_: guests (clashes with Guest), seats, persons

**Invoice**:
A payment request for one Product sent to one Guest. Becomes paid when
Telegram confirms the payment, which creates or extends the Subscription.
_Avoid_: order, checkout, bill, payment

**Payment Provider**:
A named payment-collecting account, configured with a Telegram Payments
provider token, that Products are sold through. May be restricted to one
language.
_Avoid_: payment token (the token is one field of it), gateway, merchant

### Languages

**Enabled Languages**:
The set of interface languages the bot offers. Tour Translations and Products
are expected to exist for each of them.
_Avoid_: supported languages, locales

**Default Language**:
The Enabled Language used when a Guest's language has no Translation, Product
or message of its own.
_Avoid_: fallback language, primary language, main language

### Configured messages

**Welcome Message**:
The Admin-written text a Guest receives on first contact, per language.
_Avoid_: greeting, start message, intro

**Terms Message**:
The Admin-written terms a Guest must see before purchasing, per language.
_Avoid_: terms of service, disclaimer, legal text

**Support Message**:
The Admin-written text telling a Guest how to get help, per language.
_Avoid_: help message, contact message

### Delivery behaviour

**Protect Content**:
Whether Content Items are sent so that Telegram blocks forwarding and saving.
_Avoid_: copy protection, DRM, forwarding lock

**Audio to Voice**:
Whether an uploaded audio file is converted to a Telegram voice message before
being stored as a Content Item.
_Avoid_: voice conversion, transcoding
