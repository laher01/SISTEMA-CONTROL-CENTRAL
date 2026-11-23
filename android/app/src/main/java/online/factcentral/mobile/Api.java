package online.factcentral.mobile;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.json.*;
final class Api {
 static final String BASE="https://app.nexomarnegocioseirl.online";
 private final CookieManager cookies=new CookieManager(null,CookiePolicy.ACCEPT_ORIGINAL_SERVER);
 synchronized Object get(String route)throws Exception{return request(route,null);}
 synchronized JSONObject login(String space,String login,String password)throws Exception{
  JSONObject p=new JSONObject().put("espacio",space.isEmpty()?JSONObject.NULL:space).put("login",login).put("clave",password);
  return (JSONObject)request("/api/v1/auth/login",p);
 }
 synchronized void logout()throws Exception{try{request("/api/v1/auth/logout",new JSONObject());}finally{cookies.getCookieStore().removeAll();}}
 synchronized void clear(){cookies.getCookieStore().removeAll();}
 synchronized JSONObject reviewPdf(byte[] pdf)throws Exception{
  if(pdf.length<5||pdf.length>20*1024*1024||!new String(pdf,0,5,StandardCharsets.US_ASCII).equals("%PDF-"))throw new IOException("PDF inválido o demasiado grande.");
  String boundary="FC"+UUID.randomUUID().toString().replace("-","");
  ByteArrayOutputStream data=new ByteArrayOutputStream();
  data.write(("--"+boundary+"\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\"observaciones.pdf\"\r\nContent-Type: application/pdf\r\n\r\n").getBytes(StandardCharsets.UTF_8));
  data.write(pdf);data.write(("\r\n--"+boundary+"--\r\n").getBytes(StandardCharsets.UTF_8));
  return (JSONObject)requestBytes("/api/v1/registros/sunat/observaciones",data.toByteArray(),"multipart/form-data; boundary="+boundary);
 }
 synchronized JSONObject previewRemove(String id)throws Exception {
  JSONArray ids=new JSONArray().put(id);
  return (JSONObject)request("/api/v1/documentos/previsualizar-retirada",new JSONObject().put("documentos_ids",ids));
 }
 synchronized JSONObject removeDocument(String id)throws Exception {
  if(!id.matches("[0-9a-fA-F-]{36}"))throw new IOException("Identificador inválido");
  return (JSONObject)requestMethod("/api/v1/documentos/"+id,null,"application/json","DELETE");
 }
 synchronized JSONObject uploadDocument(String filename,String mime,byte[] data)throws Exception {
  if(data==null||data.length==0||data.length>20*1024*1024)throw new IOException("Archivo vacío o superior a 20 MB.");
  String safe=filename.replaceAll("[\\r\\n\\\"]","_");
  String boundary="FC"+UUID.randomUUID().toString().replace("-","");
  ByteArrayOutputStream out=new ByteArrayOutputStream();
  out.write(("--"+boundary+"\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\""+safe+"\"\r\nContent-Type: "+mime+"\r\n\r\n").getBytes(StandardCharsets.UTF_8));
  out.write(data);out.write(("\r\n--"+boundary+"--\r\n").getBytes(StandardCharsets.UTF_8));
  return (JSONObject)requestBytes("/api/v1/documentos",out.toByteArray(),"multipart/form-data; boundary="+boundary);
 }
 private Object request(String route,JSONObject body)throws Exception{return requestBytes(route,body==null?null:body.toString().getBytes(StandardCharsets.UTF_8),"application/json");}
 private Object requestMethod(String route,byte[] body,String type,String method)throws Exception{return send(route,body,type,method);}

 private Object requestBytes(String route,byte[] body,String contentType)throws Exception{return send(route,body,contentType,body==null?"GET":"POST");}
 private Object send(String route,byte[] body,String contentType,String method)throws Exception{
  if(!route.startsWith("/api/v1/")||route.contains("..")||route.contains("\\"))throw new IOException("Ruta inválida");
  URI uri=URI.create(BASE+route);
  HttpURLConnection c=(HttpURLConnection)uri.toURL().openConnection();
  c.setInstanceFollowRedirects(false);c.setConnectTimeout(15000);c.setReadTimeout(20000);
  c.setRequestProperty("Accept","application/json");c.setRequestProperty("Origin",BASE);c.setRequestProperty("Referer",BASE+"/");
  for(var e:cookies.get(uri,Collections.emptyMap()).entrySet())for(String v:e.getValue())c.addRequestProperty(e.getKey(),v);
  try{
   c.setRequestMethod(method);
   if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type",contentType);c.setFixedLengthStreamingMode(body.length);try(OutputStream o=c.getOutputStream()){o.write(body);}}
   int code=c.getResponseCode();
   cookies.put(uri,c.getHeaderFields());
   if(code==401){clear();throw new IOException("Sesión vencida. Vuelve a ingresar.");}
   if(code==403)throw new IOException("Acceso no autorizado.");
   if(code<200||code>=300)throw new IOException("No se pudo completar la consulta ("+code+").");
   if(code==204)return new JSONObject();
   try(InputStream in=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
    byte[] buf=new byte[8192];int n;while((n=in.read(buf))!=-1){if(out.size()+n>8*1024*1024)throw new IOException("Respuesta demasiado extensa");out.write(buf,0,n);}
    if(out.size()==0)return new JSONObject();
    return new JSONTokener(out.toString("UTF-8")).nextValue();
   }
  }finally{c.disconnect();}
 }
}
