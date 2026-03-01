{\rtf1\ansi\ansicpg1251\cocoartf2759
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 FROM python:3.11-slim\
\
# \uc0\u1059 \u1089 \u1090 \u1072 \u1085 \u1072 \u1074 \u1083 \u1080 \u1074 \u1072 \u1077 \u1084  \u1089 \u1080 \u1089 \u1090 \u1077 \u1084 \u1085 \u1099 \u1077  \u1087 \u1072 \u1082 \u1077 \u1090 \u1099 : ffmpeg, libreoffice \u1080  \u1085 \u1077 \u1086 \u1073 \u1093 \u1086 \u1076 \u1080 \u1084 \u1099 \u1077  \u1079 \u1072 \u1074 \u1080 \u1089 \u1080 \u1084 \u1086 \u1089 \u1090 \u1080 \
RUN apt-get update && apt-get install -y \\\
    ffmpeg \\\
    libreoffice \\\
    libreoffice-core \\\
    && rm -rf /var/lib/apt/lists/*\
\
# \uc0\u1055 \u1088 \u1086 \u1074 \u1077 \u1088 \u1103 \u1077 \u1084  \u1091 \u1089 \u1090 \u1072 \u1085 \u1086 \u1074 \u1082 \u1091  (\u1085 \u1077 \u1086 \u1073 \u1103 \u1079 \u1072 \u1090 \u1077 \u1083 \u1100 \u1085 \u1086 , \u1085 \u1086  \u1087 \u1086 \u1083 \u1077 \u1079 \u1085 \u1086  \u1076 \u1083 \u1103  \u1083 \u1086 \u1075 \u1086 \u1074  \u1089 \u1073 \u1086 \u1088 \u1082 \u1080 )\
RUN ffmpeg -version || true\
RUN libreoffice --version || true\
\
WORKDIR /app\
COPY requirements.txt .\
RUN pip install --no-cache-dir -r requirements.txt\
COPY . .\
\
CMD ["python", "converter_bot.py"]}