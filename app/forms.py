from django import forms
from .models import Frame


class FrameCreateForm(forms.ModelForm):
    """Form for creating a new frame project."""
    
    class Meta:
        model = Frame
        fields = ['name', 'frame_image', 'feed_url']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter frame project name'
            }),
            'frame_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg'
            }),
            'feed_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://cdn.goanalytix.io/assets/casestudy/CaseStudyFeed.xml'
            })
        }
    
    def clean_frame_image(self):
        image = self.cleaned_data.get('frame_image')
        if image:
            # Check file extension
            if not image.name.lower().endswith(('.jpg', '.jpeg')):
                raise forms.ValidationError("Only JPG/JPEG files are allowed.")
            
            # Check file size (limit to 10MB)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Image file size should not exceed 10MB.")
        
        return image


class CoordinateAdjustmentForm(forms.ModelForm):
    """Form for adjusting overlay coordinates."""
    
    class Meta:
        model = Frame
        fields = ['x_coordinate', 'y_coordinate', 'width', 'height']
        widgets = {
            'x_coordinate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'y_coordinate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
            'width': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '100'
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '100'
            })
        }
    
    def clean_width(self):
        width = self.cleaned_data.get('width')
        if width and width <= 0:
            raise forms.ValidationError("Width must be greater than 0.")
        return width
    
    def clean_height(self):
        height = self.cleaned_data.get('height')
        if height and height <= 0:
            raise forms.ValidationError("Height must be greater than 0.")
        return height
