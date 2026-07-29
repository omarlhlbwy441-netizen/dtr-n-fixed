{{/*
Rafeeq Kernel Helm Helpers
*/}}

{{/* Expand the name of the chart */}}
{{- define "rafeeq.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Create chart name and version */}}
{{- define "rafeeq.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Common labels */}}
{{- define "rafeeq.labels" -}}
helm.sh/chart: {{ include "rafeeq.chart" . }}
{{ include "rafeeq.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{/* Selector labels */}}
{{- define "rafeeq.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rafeeq.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Create service account name */}}
{{- define "rafeeq.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "rafeeq.name" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
