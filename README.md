[![Build Status](https://travis-ci.com/mageops/aws-lambdas-autoscaling.svg?branch=master)](https://travis-ci.com/mageops/aws-lambdas-autoscaling)

# MageOps AWS Lambdas for Handling Autoscaling

This lambdas perform various tasks related to managing ASGs in response
to various events and conditions. They are strongly coupled to 
[MageOps infrastructure setup](https://github.com/mageops/ansible-workflow).

## Single Deploy Package

All of this handlers are be built into a single package for convenience just
the entrypoint will changed based on which one is used.

## Build

### Generating deploy package

```bash
docker run --rm --tty --volume "$(pwd):/var/app" mageops/aws-lambda-build python2 autoscaling-lambdas-deploy-package
```

#### Docker image for building lambdas

The package is built using [mageops/aws-lambda-build](https://hub.docker.com/r/mageops/aws-lambda-build).
Check the corresponding [GitHub repository](https://github.com/mageops/aws-lambda-build) for more information.

## Deploy

Lambda usage is self-documenting via ansible code, see the [MageOps provisioning code](https://github.com/mageops/ansible-workflow).
