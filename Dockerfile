{\rtf1\ansi\ansicpg1251\cocoartf2759
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fnil\fcharset0 Menlo-Regular;\f1\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;\red255\green255\blue255;\red247\green249\blue250;
}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;\cssrgb\c100000\c100000\c100000;\cssrgb\c97647\c98039\c98431;
}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\deftab720
\pard\pardeftab720\partightenfactor0

\f0\fs26 \cf2 \cb3 \expnd0\expndtw0\kerning0
# \uc0\u1057 \u1073 \u1086 \u1088 \u1082 \u1072 : 2026-03-01
\f1\fs24 \cf0 \cb1 \kerning1\expnd0\expndtw0 \
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0
\cf0 FROM python:3.11-slim\
\
# \uc0\u1059 \u1089 \u1090 \u1072 \u1085 \u1072 \u1074 \u1083 \u1080 \u1074 \u1072 \u1077 \u1084  \u1089 \u1080 \u1089 \u1090 \u1077 \u1084 \u1085 \u1099 \u1077  \u1087 \u1072 \u1082 \u1077 \u1090 \u1099  (ffmpeg, libreoffice)\
RUN apt-get update && apt-get install -y --no-install-recommends \\\
    ffmpeg \\\
    libreoffice \\\
    libreoffice-core \\\
    && apt-get clean \\\
    && rm -rf /var/lib/apt/lists/*\
\
# \uc0\u1042 \u1099 \u1074 \u1086 \u1076 \u1080 \u1084  \u1074 \u1077 \u1088 \u1089 \u1080 \u1080  \u1076 \u1083 \u1103  \u1087 \u1088 \u1086 \u1074 \u1077 \u1088 \u1082 \u1080  \u1074  \u1083 \u1086 \u1075 \u1072 \u1093  \u1089 \u1073 \u1086 \u1088 \u1082 \u1080 \
RUN ffmpeg -version || echo "FFmpeg not found" && \\\
    libreoffice --version || echo "LibreOffice not found"\
\
WORKDIR /app\
\
COPY requirements.txt .\
RUN pip install --no-cache-dir -r requirements.txt\
\
COPY . .\
\
CMD ["python", "converter_bot.py"]}