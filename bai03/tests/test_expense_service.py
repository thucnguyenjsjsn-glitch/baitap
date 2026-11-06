import pytest
from fastapi import HTTPException
from app.expense_schemas import ExpenseExtracted
from app.expense_service import check

def e(id,**kw):
    return ExpenseExtracted(submission_id=id,vendor='ABC Travel',invoice_number='INV-0042',transaction_date='2026-10-19',amount_minor=1250000,currency='VND',receipt_id='R-42',**kw)

def test_three_cases():
    first=e('E01')
    assert check(first,[])['status']=='unique_under_current_rules'
    second=ExpenseExtracted(**{**first.model_dump(),'submission_id':'E02','vendor':' abc  travel ','invoice_number':'inv-0042'})
    assert check(second,[first])['matches'][0]['submission_id']=='E01'
    third=ExpenseExtracted(submission_id='E03',vendor='ABC Travel',amount_minor=1250000,currency='VND')
    assert check(third,[first])['status']=='needs_review'

def test_hyphen_kept():
    old=e('E01')
    new=ExpenseExtracted(**{**old.model_dump(),'submission_id':'E02','receipt_id':None,'invoice_number':'INV0042'})
    assert check(new,[old])['status']=='unique_under_current_rules'

def test_different_amount_still_duplicate():
    old=e('E01');new=ExpenseExtracted(**{**old.model_dump(),'submission_id':'E02','amount_minor':1300000})
    result=check(new,[old]);assert result['status']=='duplicate_candidate';assert 'amount_minor' in result['matches'][0]['differences']

def test_invalid_money_and_currency():
    for changed in ({'amount_minor':-1},{'currency':'XYZ'}):
        item=ExpenseExtracted(**{**e('E01').model_dump(),**changed})
        with pytest.raises(HTTPException):check(item,[])
