<?php
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Recolectar los datos del formulario
    $name = $_POST['name'];
    $email = $_POST['email'];
    $message = $_POST['message'];

    // Validación básica
    if (empty($name) || empty($email) || empty($message)) {
        echo json_encode(['status' => 'error', 'message' => 'Todos los campos son requeridos.']);
        exit;
    }

    // Configuración del correo
    $to = 'alodiego@hotmail.es';  // Dirección del destinatario
    $subject = "OST - Nuevo mensaje de $name";
    $body = "Nombre: $name\nCorreo: $email\nMensaje: $message";
    $headers = "From: $email" . "\r\n" .
               "Reply-To: $email" . "\r\n" .
               "X-Mailer: PHP/" . phpversion();

    // Enviar el correo
    if (mail($to, $subject, $body, $headers)) {
        echo json_encode(['status' => 'success', 'message' => 'El mensaje se envió correctamente.']);
    } else {
        echo json_encode(['status' => 'error', 'message' => 'Hubo un error al enviar el mensaje.']);
    }
}
?>
