import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class NumberRequiredValidator:
    def validate(self, password, user=None):
        if not re.search(r'\d', password):
            raise ValidationError(
                _('Password must contain at least one digit.'),
                code='password_no_number')

    def get_help_text(self):
        return _('Your password must contain at least one digit [0-9].')
