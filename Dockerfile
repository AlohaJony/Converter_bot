{\rtf1\ansi\ansicpg1251\cocoartf2759
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 # \uc0\u1041 \u1072 \u1079 \u1086 \u1074 \u1099 \u1081  \u1086 \u1073 \u1088 \u1072 \u1079  Python (\u1086 \u1092 \u1080 \u1094 \u1080 \u1072 \u1083 \u1100 \u1085 \u1099 \u1081 , \u1084 \u1080 \u1085 \u1080 \u1084 \u1072 \u1083 \u1100 \u1085 \u1072 \u1103  \u1074 \u1077 \u1088 \u1089 \u1080 \u1103 )\
FROM python:3.11-slim\
\
# \uc0\u1059 \u1089 \u1090 \u1072 \u1085 \u1072 \u1074 \u1083 \u1080 \u1074 \u1072 \u1077 \u1084  \u1089 \u1080 \u1089 \u1090 \u1077 \u1084 \u1085 \u1099 \u1077  \u1079 \u1072 \u1074 \u1080 \u1089 \u1080 \u1084 \u1086 \u1089 \u1090 \u1080 , \u1085 \u1077 \u1086 \u1073 \u1093 \u1086 \u1076 \u1080 \u1084 \u1099 \u1077  \u1076 \u1083 \u1103  \u1082 \u1086 \u1085 \u1074 \u1077 \u1088 \u1090 \u1072 \u1094 \u1080 \u1080 \
RUN apt-get update && apt-get install -y \\\
    ffmpeg \\\
    unoconv \\\
    libreoffice \\\
    pandoc \\\
    && rm -rf /var/lib/apt/lists/*\
\
# \uc0\u1057 \u1086 \u1079 \u1076 \u1072 \u1105 \u1084  \u1088 \u1072 \u1073 \u1086 \u1095 \u1091 \u1102  \u1076 \u1080 \u1088 \u1077 \u1082 \u1090 \u1086 \u1088 \u1080 \u1102  \u1074 \u1085 \u1091 \u1090 \u1088 \u1080  \u1082 \u1086 \u1085 \u1090 \u1077 \u1081 \u1085 \u1077 \u1088 \u1072 \
WORKDIR /app\
\
# \uc0\u1050 \u1086 \u1087 \u1080 \u1088 \u1091 \u1077 \u1084  \u1092 \u1072 \u1081 \u1083  \u1089  \u1079 \u1072 \u1074 \u1080 \u1089 \u1080 \u1084 \u1086 \u1089 \u1090 \u1103 \u1084 \u1080  Python\
COPY requirements.txt .\
\
# \uc0\u1059 \u1089 \u1090 \u1072 \u1085 \u1072 \u1074 \u1083 \u1080 \u1074 \u1072 \u1077 \u1084  Python-\u1073 \u1080 \u1073 \u1083 \u1080 \u1086 \u1090 \u1077 \u1082 \u1080 \
RUN pip install --no-cache-dir -r requirements.txt\
\
# \uc0\u1050 \u1086 \u1087 \u1080 \u1088 \u1091 \u1077 \u1084  \u1074 \u1077 \u1089 \u1100  \u1082 \u1086 \u1076  \u1073 \u1086 \u1090 \u1072  \u1074  \u1082 \u1086 \u1085 \u1090 \u1077 \u1081 \u1085 \u1077 \u1088 \
COPY . .\
\
# \uc0\u1059 \u1082 \u1072 \u1079 \u1099 \u1074 \u1072 \u1077 \u1084  \u1082 \u1086 \u1084 \u1072 \u1085 \u1076 \u1091  \u1076 \u1083 \u1103  \u1079 \u1072 \u1087 \u1091 \u1089 \u1082 \u1072  \u1073 \u1086 \u1090 \u1072 \
CMD ["python", "converter_bot.py"]}