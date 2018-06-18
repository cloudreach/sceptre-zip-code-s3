"""
Example template to create IAM role
"""
from troposphere import Template, Parameter, Ref, Output, GetAtt
from troposphere.iam import Role


class SceptreResource(object):
    def __init__(self, sceptre_user_data):
        self.sceptre_user_data = sceptre_user_data
        self.template = Template()
        self.build_role()

    def build_role(self):
        name = self.template.add_parameter(Parameter("Name", Type="String"))

        kwargs = self.sceptre_user_data
        kwargs["RoleName"] = Ref(name)

        role = self.template.add_resource(Role("Role", **kwargs))

        self.template.add_output(Output("Arn", Value=GetAtt(role, "Arn")))


def sceptre_handler(sceptre_user_data):
    return SceptreResource(sceptre_user_data).template.to_json()
