from django.db import models

class GithubRun(models.Model):
    id = models.IntegerField(verbose_name="ID", primary_key=True)
    uuid = models.CharField(verbose_name="uuid", max_length=100)
    status = models.CharField(verbose_name="status", max_length=100)
    github_run_id = models.BigIntegerField(null=True, blank=True)


class ClientProfile(models.Model):
    name = models.CharField(max_length=100, verbose_name="Profile Name")
    variant = models.CharField(max_length=50, default='client', verbose_name="Variant")
    exename = models.CharField(max_length=100, default='rustdesk', verbose_name="EXE Name")
    appname = models.CharField(max_length=100, default='rustdesk', verbose_name="App Name")
    compname = models.CharField(max_length=100, default='Purslane Ltd', verbose_name="Company Name")
    androidappid = models.CharField(max_length=100, default='com.carriez.flutter_hbb', verbose_name="Android App ID")
    serverIP = models.CharField(max_length=200, blank=True, default='')
    key = models.CharField(max_length=500, blank=True, default='')
    apiServer = models.CharField(max_length=200, blank=True, default='')
    urlLink = models.CharField(max_length=200, blank=True, default='')
    downloadLink = models.CharField(max_length=200, blank=True, default='')
    icon_image = models.ImageField(upload_to='profiles/icons/', null=True, blank=True)
    logo_image = models.ImageField(upload_to='profiles/logos/', null=True, blank=True)
    privacy_image = models.ImageField(upload_to='profiles/privacy/', null=True, blank=True)
    iconbase64 = models.TextField(blank=True, default='')
    logobase64 = models.TextField(blank=True, default='')
    privacybase64 = models.TextField(blank=True, default='')
    config_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.variant})"
