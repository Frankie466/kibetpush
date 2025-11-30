from django import forms

class PaymentForm(forms.Form):
    phone_number = forms.CharField(label='Phone_Number', max_length=15)
    amount = forms.CharField(label='Amount', min_length=1)
    