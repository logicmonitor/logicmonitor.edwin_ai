class ModuleDocFragment(object):
    DOCUMENTATION = r"""
    options:
        access_id:
            description:
                - Access ID from an Edwin API token.
                - If you do not have a suitable API token, please contact your Edwin admin.
            required: true
            type: str
        access_key:
            description:
                - Access Key from an Edwin API token.
                - If you do not have a suitable API token, please contact your Edwin admin.
            required: true
            type: str
    """
