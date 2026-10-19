import re

from django.utils import timezone
from rest_framework import serializers

from listings.models import Property, Status

from .models import Inspection, InspectionStatus, PaymentChoice, PaymentStatus

PHONE_PATTERN = re.compile(r'^\+?[0-9 ()-]{10,20}$')


class InspectionCreateSerializer(serializers.ModelSerializer):
    """
    Visitor-facing request. Status, payment status and fee are never taken from the client:
    a new inspection is always pending, and an in-person or unpaid request is always unpaid.
    """

    date = serializers.DateField(source='preferred_date')
    property = serializers.PrimaryKeyRelatedField(queryset=Property.objects.filter(status=Status.PUBLISHED))
    payment_choice = serializers.ChoiceField(choices=PaymentChoice.choices, required=False)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = Inspection
        fields = [
            'id', 'reference', 'name', 'phone', 'email', 'property', 'date', 'note',
            'payment_choice', 'fee_amount', 'payment_status', 'status',
        ]
        read_only_fields = ['id', 'reference', 'fee_amount', 'payment_status', 'status']

    def validate_phone(self, value):
        value = value.strip()
        if not PHONE_PATTERN.match(value):
            raise serializers.ValidationError('Enter a valid phone number.')
        return value

    def validate_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError('Choose today or a later date.')
        return value

    def validate(self, attrs):
        prop = attrs['property']
        if prop.inspection_fee > 0 and not attrs.get('payment_choice'):
            raise serializers.ValidationError({'payment_choice': 'Choose how you will pay the inspection fee.'})
        if prop.inspection_fee <= 0:
            attrs['payment_choice'] = PaymentChoice.IN_PERSON  # nothing to pay
        return attrs

    def create(self, validated_data):
        prop = validated_data['property']
        fee = prop.inspection_fee
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        validated_data['email'] = validated_data['email'].strip().lower()
        return Inspection.objects.create(
            user=user,
            fee_amount=fee,
            payment_status=PaymentStatus.UNPAID if fee > 0 else PaymentStatus.NOT_REQUIRED,
            status=InspectionStatus.PENDING,  # confirmation only ever happens later, by staff
            **validated_data,
        )
