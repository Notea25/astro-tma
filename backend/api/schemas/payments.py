from pydantic import BaseModel


class CreateInvoiceRequest(BaseModel):
    product_id: str


class CreateInvoiceResponse(BaseModel):
    invoice_url: str
    product_id: str
    stars_amount: int


class ProductInfo(BaseModel):
    id: str
    name: str
    description: str
    stars: int
    # Effective ruble price (catalogue default with admin Redis override).
    # 0 means no ruble price configured — frontend should hide the ruble
    # button in that case.
    price_rub: int = 0
    type: str   # "one_time" | "subscription"


class ProductsCatalogue(BaseModel):
    products: list[ProductInfo]
    # Per-user YuKassa availability. False when credentials are absent or
    # the user's confirmed birth country is not eligible for ruble payments.
    card_payments_available: bool = False
