# partners/management/commands/check_subscriptions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from partner.models import PartnerSubscription, PartnerPlan, PartnerWallet, WalletTransaction
from decimal import Decimal

class Command(BaseCommand):
    help = 'Deactivates expired subscriptions and resets wallet balances for WALLET_CREDIT plans.'

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write("Starting expiration process...")
        
        # --- 1. Process Expired Time-Based Subscriptions ---
        expired_subscriptions = PartnerSubscription.objects.filter(
            is_active=True,
            plan__plan_type=PartnerPlan.PlanType.SUBSCRIPTION, # Filter by plan type
            end_date__lt=now
        )
        
        if expired_subscriptions.exists():
            for sub in expired_subscriptions:
                sub.is_active = False
                sub.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Deactivated subscription for {sub.partner.business_name} (Plan: {sub.plan.name})."
                ))
        else:
            self.stdout.write("No expired time-based subscriptions to process.")
        
        self.stdout.write("-" * 50)

        # --- 2. Process Expired Wallet Balances ---
        # This will only find wallets with a balance_expires_at date,
        # which is set exclusively for WALLET_CREDIT plans.
        expired_wallets = PartnerWallet.objects.filter(
            balance_expires_at__lt=now,
            balance__gt=Decimal('0.00')
        ).select_related('partner', 'partner__subscriptions') # Add select_related for efficiency

        if expired_wallets.exists():
            for wallet in expired_wallets:
                expired_balance = wallet.balance
                
                # Deactivate the related subscription for this wallet plan
                wallet_subscription = wallet.partner.subscriptions.filter(plan__plan_type=PartnerPlan.PlanType.WALLET_CREDIT, is_active=True).first()
                if wallet_subscription:
                    wallet_subscription.is_active = False
                    wallet_subscription.save()

                # Log the expiry transaction and reset the balance
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type=WalletTransaction.TransactionType.EXPIRY,
                    amount=-expired_balance,
                    details=f"Balance expired from Wallet Credit plan."
                )
                
                wallet.balance = Decimal('0.00')
                wallet.balance_expires_at = None  # Reset the expiry date
                wallet.save()
                
                self.stdout.write(self.style.SUCCESS(
                    f"Reset wallet balance for {wallet.partner.business_name} and deactivated related subscription."
                ))
        else:
            self.stdout.write("No expired wallet balances to process.")
        
        self.stdout.write(self.style.SUCCESS("Expiration process finished."))