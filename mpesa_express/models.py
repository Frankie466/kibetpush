from django.db import models

class Transaction(models.Model):  # Fixed typo in class name (Transacttion → Transaction)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    checkout_id = models.CharField(max_length=100, unique=True)
    mpesa_code = models.CharField(max_length=15, blank=True, null=True)  # Allow null initially
    status = models.CharField(max_length=20, default="Pending")  # Default status to 'Pending'
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mpesa_code or 'N/A'} - {self.amount} KES"
