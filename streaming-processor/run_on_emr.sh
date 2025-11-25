#!/bin/bash
#
# Run Kinesis Stream Reader on AWS EMR
# 
# This script submits a Spark Structured Streaming job to EMR
# that reads from Kinesis and writes processed data to S3
#

set -e

# ============================================================================
# CONFIGURATION - Update these values
# ============================================================================

EMR_CLUSTER_ID="${EMR_CLUSTER_ID:-j-XXXXXXXXXXXXX}"  # Your EMR cluster ID
KINESIS_STREAM_NAME="${KINESIS_STREAM_NAME:-stock-market-stream}"
S3_BUCKET="${S3_BUCKET:-your-bucket-name}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# S3 paths
S3_CODE_PATH="s3://${S3_BUCKET}/spark/code/"
S3_OUTPUT_PATH="s3://${S3_BUCKET}/processed/"
S3_LOGS_PATH="s3://${S3_BUCKET}/logs/"

echo "============================================================"
echo "🚀 Submitting Spark Streaming Job to EMR"
echo "============================================================"
echo "Cluster ID: ${EMR_CLUSTER_ID}"
echo "Kinesis Stream: ${KINESIS_STREAM_NAME}"
echo "S3 Bucket: s3://${S3_BUCKET}"
echo "Region: ${AWS_REGION}"
echo "============================================================"

# ============================================================================
# STEP 1: Upload code to S3
# ============================================================================

echo ""
echo "📦 Step 1: Uploading code to S3..."

# Upload the Python script
aws s3 cp kinesis_reader_emr.py "${S3_CODE_PATH}kinesis_reader_emr.py"

# Upload dependencies if needed
if [ -f requirements.txt ]; then
    aws s3 cp requirements.txt "${S3_CODE_PATH}requirements.txt"
fi

echo "✅ Code uploaded to ${S3_CODE_PATH}"

# ============================================================================
# STEP 2: Submit Spark job as EMR Step
# ============================================================================

echo ""
echo "🔥 Step 2: Submitting Spark job to EMR cluster..."

STEP_ID=$(aws emr add-steps \
    --cluster-id "${EMR_CLUSTER_ID}" \
    --region "${AWS_REGION}" \
    --steps \
    Type=Spark,Name="Kinesis-Stream-Reader",\
ActionOnFailure=CONTINUE,\
Args=[\
--deploy-mode,cluster,\
--master,yarn,\
--packages,org.apache.spark:spark-sql-kinesis_2.12:3.3.0,\
--conf,spark.yarn.submit.waitAppCompletion=false,\
--conf,spark.sql.streaming.schemaInference=true,\
--conf,spark.executor.memory=4g,\
--conf,spark.executor.cores=2,\
--conf,spark.dynamicAllocation.enabled=true,\
--conf,spark.streaming.stopGracefullyOnShutdown=true,\
"${S3_CODE_PATH}kinesis_reader_emr.py"\
] \
    --query 'StepIds[0]' \
    --output text)

echo "✅ Step submitted successfully!"
echo "   Step ID: ${STEP_ID}"

# ============================================================================
# STEP 3: Monitor the step
# ============================================================================

echo ""
echo "📊 Step 3: Monitoring step execution..."
echo "   (Press Ctrl+C to stop monitoring, the job will continue running)"
echo ""

while true; do
    STATUS=$(aws emr describe-step \
        --cluster-id "${EMR_CLUSTER_ID}" \
        --step-id "${STEP_ID}" \
        --region "${AWS_REGION}" \
        --query 'Step.Status.State' \
        --output text)
    
    echo "[$(date +%T)] Step Status: ${STATUS}"
    
    if [[ "${STATUS}" == "COMPLETED" ]]; then
        echo "✅ Step completed successfully!"
        break
    elif [[ "${STATUS}" == "FAILED" ]] || [[ "${STATUS}" == "CANCELLED" ]]; then
        echo "❌ Step failed or was cancelled"
        echo "Check logs at: ${S3_LOGS_PATH}"
        exit 1
    fi
    
    sleep 10
done

# ============================================================================
# STEP 4: Show output location
# ============================================================================

echo ""
echo "============================================================"
echo "✅ Job is running successfully!"
echo "============================================================"
echo "📊 Streaming data from Kinesis: ${KINESIS_STREAM_NAME}"
echo "💾 Output location: ${S3_OUTPUT_PATH}"
echo "📝 Logs location: ${S3_LOGS_PATH}"
echo ""
echo "To check output data:"
echo "  aws s3 ls ${S3_OUTPUT_PATH} --recursive"
echo ""
echo "To stop the job:"
echo "  aws emr cancel-steps --cluster-id ${EMR_CLUSTER_ID} --step-ids ${STEP_ID}"
echo ""
echo "To view Spark UI:"
echo "  1. Enable SSH tunnel to EMR master node"
echo "  2. Access: http://master-node:8088/proxy/application_id/"
echo "============================================================"



