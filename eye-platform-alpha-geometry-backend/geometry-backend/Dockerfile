FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends bash git build-essential cmake ninja-build && rm -rf /var/lib/apt/lists/*
ENV PORT=8000
ENV PATH="/opt/eye-venv/bin:${PATH}"
ENV EYE_TRIPOSR_SOURCE=/opt/triposr
ENV EYE_TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ENV EYE_RECONSTRUCTION_PROVIDER=dpt-depth-mesh
ENV EYE_DPT_MODEL=Intel/dpt-hybrid-midas
ENV PYTHONPATH="/opt/triposr:/app"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static
COPY scripts/install_triposr.sh /usr/local/bin/install_triposr
COPY scripts/verify_ai_runtime.sh /usr/local/bin/verify_ai_runtime
# DPT is the default provider and must install cleanly; it needs no marching-cubes extension.
RUN python -m venv /opt/eye-venv \
	&& /opt/eye-venv/bin/pip install --upgrade pip setuptools \
	&& /opt/eye-venv/bin/pip install -r requirements.txt \
	&& /opt/eye-venv/bin/pip install --index-url "$EYE_TORCH_INDEX_URL" torch torchvision \
	&& /opt/eye-venv/bin/pip install "numpy==1.26.4" "transformers==4.35.0" "huggingface-hub<0.18" \
	&& /opt/eye-venv/bin/python -c "from transformers import DPTForDepthEstimation, DPTImageProcessor; m='Intel/dpt-hybrid-midas'; DPTImageProcessor.from_pretrained(m); DPTForDepthEstimation.from_pretrained(m)"
# TripoSR/torchmcubes is a best-effort optional extra provider; its failure must never break the image.
RUN (EYE_TRIPOSR_SOURCE=/opt/triposr VENV=/opt/eye-venv bash /usr/local/bin/install_triposr \
	&& PYTHON=/opt/eye-venv/bin/python bash /usr/local/bin/verify_ai_runtime) \
	|| echo "TripoSR optional install unavailable; DPT provider remains default and functional"
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
