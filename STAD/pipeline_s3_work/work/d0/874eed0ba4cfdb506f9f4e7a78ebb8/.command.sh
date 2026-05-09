#!/bin/bash -ue
aws s3 cp --recursive 'features'         's3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/fe_output/20260421_stad_fe_v1/features/'
aws s3 cp --recursive 'pair_features'         's3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/fe_output/20260421_stad_fe_v1/pair_features/'
echo "Uploaded to s3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/fe_output/20260421_stad_fe_v1/"
