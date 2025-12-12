import re
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _


#Custom function to validate phone numbers 
def validate_phone_number(value):
    '''
    Custom validator for phone numbers.\n
    <br>
    Regex explanation: \n
    ^                 - Start of the string \n
    \\+?              - Optional leading plus sign (for international codes) \n 
    [\\d\\s\\-\\(\\)]+ - One or more digits, spaces, hyphens, or parentheses \n 
    \\$                - End of the string \n 
    <br>
    This regex allows for formats like: \n
    +123 456 7890 \n
    (123) 456-7890 \n
    123-456-7890 \n
    1234567890 \n
    +44 20 7946 0958 \n
    '''
    
    phone_regex = r"^\+?[\d\s\-\(\)]+$"

    if not re.fullmatch(phone_regex, value):
        raise ValidationError(
            _("Enter a valid phone number. Only digits, spaces, hyphens, parentheses, and an optional leading '+' are allowed."),
            code='invalid_phone_number')


#Custom function to validate file size
def validate_file_size(file):
    limit_mb = 5
    if file.size > limit_mb * 1024 * 1024:
        raise ValidationError(_(f"File size should not exceed {limit_mb} MB."))


#Custom function to validate file format
file_validators = [
    validate_file_size,
    FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']),
]