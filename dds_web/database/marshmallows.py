from dds_web import ma


class UserSchema(ma.Schema):
    class Meta:
        # The following fields will be shown when returned in request
        # Change for later -- hide sensitive info etc
        fields = (
            "id",
            "first_name",
            "last_name",
            "username",
            "password",
            "settings",
            "email",
            "phone",
            "admin",
        )


class FacilitySchema(ma.Schema):
    class Meta:
        # The following fields will be shown when returned in request
        # Change for later -- hide sensitive info etc
        fields = ("id", "name", "username", "password", "settings", "email", "phone")


class ProjectSchema(ma.Schema):
    class Meta:
        # The following fields will be shown when returned in request
        # Change for later -- hide sensitive info etc
        fields = (
            "id",
            "time",
            "category",
            "order_date",
            "delivery_date",
            "status",
            "sensitive",
            "description",
            "pi",
            "owner",
            "facility",
            "size",
            "delivery_option",
            "public_key",
            "private_key",
            "nonce",
        )


class S3Schema(ma.Schema):
    class Meta:
        # The following fields will be shown when returned in request
        # Change for later -- hide sensitive info etc
        fields = ("id", "project_id")


class FileSchema(ma.Schema):
    class Meta:
        # The following fields will be shown when returned in request
        # Change for later -- hide sensitive info etc
        fields = (
            "id",
            "name",
            "directory_path",
            "size",
            "format",
            "compressed",
            "public_key",
            "salt",
            "time_uploaded",
            "project_id",
        )


user_schema = UserSchema()
users_schema = UserSchema(many=True)

fac_schema = FacilitySchema()
facs_schema = FacilitySchema(many=True)

project_schema = FacilitySchema()
projects_schema = FacilitySchema(many=True)

s3_schema = FacilitySchema()
s3s_schema = FacilitySchema(many=True)

file_schema = FacilitySchema()
files_schema = FacilitySchema(many=True)
