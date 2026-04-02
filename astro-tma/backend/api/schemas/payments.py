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
    type: str   # "one_time" | "subscription"
