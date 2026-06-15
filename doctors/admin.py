from django.contrib import admin

from doctors.models import Doctor, DoctorSlot

admin.site.register(Doctor)
admin.site.register(DoctorSlot)
