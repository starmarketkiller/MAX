import pytest

from funding_v1.first_revenue import FirstRevenueStore
from funding_v1.lead_research_cycle import (attach_delivery, book_observed_payment,
                                            open_prospect, public_status)
from orchestrator_v1.core.ledger import EventLedger


def store(tmp_path):
    return FirstRevenueStore(tmp_path / "first_revenue.json",
                             ledger=EventLedger(tmp_path / "ledger.jsonl"))


def items(count=15):
    return [{"display_name": f"Lead {index}", "source_url": f"https://example.com/lead-{index}"}
            for index in range(count)]


def interested(book, lead_id):
    book.record_manual_send(lead_id, approved_fingerprint="fp", draft_fingerprint="fp",
                            approved_by="owner", receipt_reference="gmail-observed")
    book.transition_lead(lead_id, "REPLIED")
    book.transition_lead(lead_id, "INTERESTED")


def test_open_requires_a_public_source_and_does_not_send(tmp_path):
    book = store(tmp_path)
    with pytest.raises(ValueError):
        open_prospect(book, display_name="Ada", company="Ada Web", source_url="ada.example")
    opened = open_prospect(book, display_name="Ada", company="Ada Web",
                           source_url="https://ada.example")
    assert opened["status"] == "CONTACT_READY"
    assert opened["sends_mail"] is False
    again = open_prospect(book, display_name="Ada", company="Ada Web",
                          source_url="https://ada.example")
    assert again["created"] is False and again["lead_id"] == opened["lead_id"]
    assert public_status(book)["moves_money"] is False


def test_delivery_and_payment_stay_closed_until_the_facts_exist(tmp_path):
    book = store(tmp_path)
    opened = open_prospect(book, display_name="Ada", company="Ada Web",
                           source_url="https://ada.example")
    with pytest.raises(ValueError, match="15 to 20"):
        attach_delivery(book, opened["lead_id"], items(14))
    with pytest.raises(ValueError, match="interested"):
        attach_delivery(book, opened["lead_id"], items())
    interested(book, opened["lead_id"])
    with pytest.raises(ValueError, match="unique https"):
        bad = items()
        bad[1]["source_url"] = bad[0]["source_url"]
        attach_delivery(book, opened["lead_id"], bad)
    packed = attach_delivery(book, opened["lead_id"], items())
    assert packed["count"] == 15 and packed["sent"] is False
    with pytest.raises(ValueError, match="Revolut"):
        book_observed_payment(book, lead_id=opened["lead_id"], external_reference="x")
    revenue = book_observed_payment(book, lead_id=opened["lead_id"],
                                    external_reference="revolut-observed-1001", cost=0)
    assert revenue["amount"] == 25 and revenue["gross_margin"] == 25
    assert book.snapshot()["leads"][0]["status"] == "WON"
