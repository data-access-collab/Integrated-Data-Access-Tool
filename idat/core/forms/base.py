from django import forms


class IdatBaseForm(forms.Form):
    """Provide css classes to target through tailwind."""

    required_css_class = "required"
    error_css_class = "error"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.label_suffix = ""


class IdatBaseModelForm(forms.ModelForm):
    """Provide css classes to target through tailwind."""

    required_css_class = "required"
    error_css_class = "error"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
