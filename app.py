from flask import Flask, request, render_template, jsonify
#from flask_bootstrap5 import Bootstrap
import xml.etree.ElementTree as ET
import json
import settings
import logging
from utils import conn_to_redis, get_data_from_redis


# Зчитування параметрів додатку з конфігураційного файлу
conf = settings.Config('config.ini')

# Налаштування логування
try:
    settings.configure_logging(conf)
    logger = logging.getLogger(__name__)
    logger.info("Логування налаштовано успішно.")
except Exception as e:
    # Якщо виникає помилка при налаштуванні логування, додаток припиняє роботу
    print(f"Помилка налаштування логування: {e}")
    print("Програму зупинено!")
    exit(-1)

logger.debug("Початок ініціалізації додатку")

app = Flask(__name__)
logger.info("Додаток Flask ініціалізовано.")

@app.template_filter('fromstring')
def fromstring_filter(xml_string):
    """Парсит XML-строку в ElementTree.Element для использования в шаблоне"""
    try:
        return ET.fromstring(xml_string)
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        return None

@app.route('/<message_uuid>')
def evidense_previewer(message_uuid):

    # Get returnurl parameter from URL
    returnurl = request.args.get("returnurl")

    # show error if returnurl is not provided
    if not returnurl:
        return render_template("error.html",
                               error_message="Відсутній обовʼязковий параметр 'returnurl'",
                               error_details="URL повинен містити параметр returnurl. Приклад: /?returnurl=https://example.com"), 400
    # show error if message_uuid is not provided
    if not message_uuid:
        return render_template("error.html",
                               error_message="Відсутній обовʼязковий параметр 'message_uuid'",
                               error_details="URL повинен містити параметр message_uuid. Приклад: /3245234089573246345"), 400

    print(message_uuid)
    print(returnurl)

    redis_conn = conn_to_redis(conf.redis_url)
    data = get_data_from_redis(message_uuid, redis_conn)
    redis_conn.close()
    # json_raw = testdata.evidence
    # print(json_raw)
    # data = json.loads(json_raw)


    if data is None:
        return render_template("error.html",
                               error_message="Data not found",
                               error_details=f"Data not found in Redis by id: {message_uuid}"), 404


    if (not data["preview"]):
        return render_template("error.html",
                               error_message="Data is not previewable",
                               error_details=f"Data is not previewable in Redis by id: {message_uuid}"), 400


    # log content type of incoming message
    logger.debug(f"DATA: {data}")
    logger.debug(f'Evidences: {data["evidences"]}')
    logger.debug(f'Evidences: { data["evidences"][0] }')
    logger.debug(f'Evidences: {data["evidences"][0]["content_type"]}')

    first_evidence_content_type = data["evidences"][0]["content_type"]


    try:
        if (first_evidence_content_type == "application/pdf"):
            logger.debug("Evidences type PDF")
            # list for evidence PDFs
            pdf_list = []
            logger.debug("Start formating list of PDF evidences")
            for evidence in data["evidences"]:
                logger.debug(f"Iterated evidence {evidence}")
                pdf_list.append({
                    "title": evidence["cid"],
                    "pdf_preview": evidence["content"]
                })

            logger.debug("End formating list of PDF evidences")
            logger.debug(f"List of PDF evidences: {pdf_list}")
            logger.debug(f"Message UUID: {message_uuid}")
            logger.debug(f"Return URL: {returnurl}")

            return render_template("pdf.html", returnurl=returnurl, message_uuid=message_uuid, pdf_list=pdf_list)

        elif (first_evidence_content_type == "application/xml"):
            logger.debug("Evidence type XML")

            logger.debug(f"Data for preview: {data}")
            # List for XMLs
            xml_list = []

            for evidence in data["evidences"]:
                xml_list.append({
                    "title": evidence["cid"],
                    "xml": evidence["content"]
                })

            logger.debug("Start formating list of XML evidences")
            logger.debug(f"XML evidences: {xml_list}")
            return render_template("index.html", xml_list=xml_list, message_uuid=message_uuid, returnurl=returnurl)

        else :
            return render_template("error.html",
                               error_message="Unsupported content type",
                               error_details=f"Unsupported content type: {first_evidence_content_type}"), 400

    except Exception as e:
        logger.error(f"Error while decoding evidence{e}")

        return render_template("error.html",
                               error_message="Error while decoding evidence",
                               error_details="Error while decoding evidence"), 400

    # List for XMLs
    xml_list = []

    for evidence in data["evidences"]:
        xml_list.append({
            "title": evidence["cid"],
            "xml": evidence["content"]
        })

    return render_template("index.html", xml_list=xml_list, message_uuid=message_uuid, returnurl=returnurl)


@app.route('/submit', methods=['POST'])
def submit_approvals():
    """Обробляємо отримані статуси чекбоксів"""
    data = request.get_json()
    logger.info("Отримано відповідь з апрувами.")
    logger.debug(data)
    approvals = data.get('approvals', {})

    logger.debug("Підключення до Redis для оновлення стану апрувів.")
    redis_conn = conn_to_redis(conf.redis_url)
    if redis_conn is None:
        logger.error("Зʼєднання з Redis провалено")
        return jsonify({"status": "error", "message": "Redis connection failed"}), 500
    json_data = get_data_from_redis(data["message_uuid"], redis_conn)

    for doc_id, is_approved in approvals.items():
        logger.debug(f"Документ {doc_id}: {'Затверджено' if is_approved else 'Не затверджено'}")
        for evidence in json_data["evidences"]:
            if doc_id == evidence["cid"]:
                evidence["permit"] = is_approved

    json_data["preview"] = False

    redis_conn.set(f"oots:message:response:evidence:{data['message_uuid']}", json.dumps(json_data), conf.redis_ttl)
    redis_conn.set(f"oots:message:request:permit:{data['message_uuid']}", json.dumps(True), conf.redis_ttl)
    redis_conn.close()

    return jsonify({
        "status": "success",
        "message": "Approvals received",
        "approvals": approvals
    })


if __name__ == '__main__':
    app.run(port=8000, host="0.0.0.0", debug=True)