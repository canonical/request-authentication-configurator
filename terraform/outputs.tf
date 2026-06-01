output "app_name" {
  value = juju_application.request_authentication_integrator.name
}

output "provides" {
  value = {}
}

output "requires" {
  value = {
    oauth            = "oauth"
    m2m_request_auth = "request-auth-m2m",
    ui_request_auth  = "request-auth-ui"
  }
}
