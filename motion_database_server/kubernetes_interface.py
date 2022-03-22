#!/usr/bin/env python
#
# Copyright 2019 DFKI GmbH.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the
# following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
sources:
https://www.programcreek.com/python/example/96324/kubernetes.client.V1Container
https://github.com/kubernetes-client/python/issues/489

"""
from kubernetes import client, config

def create_job_command_string(job_desc):
    repo_url = job_desc["repo_url"]
    exec_dir = job_desc["exec_dir"]
    command = job_desc["command"]
    command_str = """ mkdir work; cd work;
                        apt-get update; apt-get install -y git; 
                        git clone --recurse-submodules {0};
                        cd {1};
                        {2}  
                        """.format(repo_url, exec_dir, command)
    return command_str

def create_aws_job_command_string(job_desc):
    repo_url = job_desc["repo_url"]
    exec_dir = job_desc["exec_dir"]
    command = job_desc["command"]
    out_dir = job_desc["out_dir"]

    aws_url =job_desc["aws"]["url"] 
    aws_access_key = job_desc["aws"]["access_key"]
    aws_secret_key = job_desc["aws"]["secret_key"]
    src_bucket = job_desc["aws"]["src_bucket"]
    dst_bucket = job_desc["aws"]["dst_bucket"]
    command_str = """ mkdir work; cd work;
                        apt-get update; apt-get install -y git; 
                        pip3 install awscli
                        export AWS_ACCESS_KEY_ID={1}
                        export AWS_SECRET_ACCESS_KEY={2}
                        git clone --recurse-submodules {3};
                        cd {4};
                        aws --endpoint-url {0} s3 cp  s3://{6} ./{6} --recursive
                        aws --endpoint-url {0} s3 rb  s3://{6} --force
                        mkdir {7}
                        {5}  
                        aws --endpoint-url {0} s3 mb s3://{8}
                        aws --endpoint-url {0} s3 cp ./{7} s3://{8} --recursive
                        """.format(aws_url, aws_access_key,  aws_secret_key,
                                    repo_url, exec_dir, command,
                                    src_bucket, out_dir, dst_bucket)
    return command_str

def create_resources_spec_from_dict(resources):
    # https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/
    requests = dict()
    limits = dict()
    if "n_gpus" in resources:
        requests["nvidia.com/gpu"] = resources["n_gpus"]
        limits["nvidia.com/gpu"] = resources["n_gpus"]
    if "cpu" in resources:
        requests["cpu"] = resources["cpu"]["request"]
        limits["cpu"] = resources["cpu"]["limit"]
    if "memory" in resources:
        requests["memory"] = resources["memory"]["request"]
        limits["memory"] = resources["memory"]["limit"]
    if "storage" in resources:
        requests["storage"] = resources["storage"]["request"]
        limits["storage"] = resources["storage"]["limit"]
    res_spec = client.V1ResourceRequirements(requests=requests, limits=limits)
    print("set requirements", resources)
    return res_spec

def create_pod_template(name, image, job_desc, restart_policy="Never", res_spec=None):
    # Configure Pod template container
    # https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Container.md
    
    if "aws" in job_desc and job_desc["aws"] is not None:
        env = [client.V1EnvVar(name="AWS_ACCESS_KEY_ID", value=job_desc["aws"]["access_key"]),
                client.V1EnvVar(name="AWS_SECRET_ACCESS_KEY", value=job_desc["aws"]["secret_key"])]

        command_str = create_aws_job_command_string(job_desc)
    else:
        env = []
        command_str = create_job_command_string(job_desc)

    container = client.V1Container(
        name=name, image=image,resources=res_spec, env=env,
        command=["bin/bash"],
        args=["-c", command_str]
        )
    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": name}),
        spec=client.V1PodSpec(containers=[container], restart_policy=restart_policy))
    return template


def create_deployment(namespace, name, template):
    # Create the specification of deployment
    spec = client.ExtensionsV1beta1DeploymentSpec(replicas=1, template=template)
    # Instantiate the deployment object
    deployment = client.ExtensionsV1beta1Deployment(
        api_version="extensions/v1beta1", kind="Deployment",
        metadata=client.V1ObjectMeta(name= name), spec=spec)
    api_instance = client.ExtensionsV1beta1Api()
    api_response = api_instance.create_namespaced_deployment(body=deployment, namespace=namespace)
    print("Deployment created. status='%s'" % str(api_response.status))


def create_job(namespace, name, template):
    # Create the specification of deployment
    spec = client.V1JobSpec(template=template)

    # Instantiate the job object
    job = client.V1Job(metadata=client.V1ObjectMeta(name= name), spec=spec)
    
    #api_instance = client.CoreV1Api(client.ApiClient())
    api_instance = client.BatchV1Api(client.ApiClient())
    #api_response = api_instance.create_namespaced_pod(body=job, namespace=namespace)
    api_response = api_instance.create_namespaced_job(body=job, namespace=namespace)
    print("Job created. status='%s'" % str(api_response.status))


def load_kube_config(kube_config_file):
    config.load_kube_config(kube_config_file)

def start_kube_job(namespace, job_name, image_name, job_desc, resources=None):
    res_spec = None
    if resources is not None:
        res_spec = create_resources_spec_from_dict(resources)
    template = create_pod_template(job_name,  image_name, job_desc, restart_policy="Never", res_spec=res_spec)
    create_job(namespace, job_name, template)

def stop_kube_job(namespace, name):
    api_instance = client.BatchV1Api(client.ApiClient())
    api_response = api_instance.delete_namespaced_job(
        name=name, namespace=namespace,
        body=client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=5))
    print("Job deleted. status='%s'" % str(api_response.status))


def start_kube_deployment(namespace, job_name, image_name, job_desc, resources=None):
    res_spec = None
    if resources is not None:
        res_spec = create_resources_spec_from_dict(resources)
    template = create_pod_template(job_name,  image_name, job_desc, restart_policy="Always", res_spec=res_spec)
    create_deployment(namespace, job_name, template)
    
def stop_kube_deployment(namespace, name):
    api_instance = client.ExtensionsV1beta1Api()
    api_response = api_instance.delete_namespaced_deployment(
        name=name, namespace=namespace,
        body=client.V1DeleteOptions(propagation_policy='Foreground', grace_period_seconds=5))
    print("Deployment deleted. status='%s'" % str(api_response.status))#

