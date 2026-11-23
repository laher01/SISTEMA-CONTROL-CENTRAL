package online.factcentral.mobile;
import org.junit.Test;
import static org.junit.Assert.*;
public class RolePolicyOperationsTest {
 @Test public void onlyGestorUploads(){assertTrue(RolePolicy.upload("GESTOR"));assertFalse(RolePolicy.upload("ADMINISTRADOR"));assertFalse(RolePolicy.upload("USUARIO"));}
 @Test public void deletionNeedsOperationalRole(){assertTrue(RolePolicy.remove("GESTOR"));assertTrue(RolePolicy.remove("USUARIO"));assertTrue(RolePolicy.remove("ADMINISTRADOR"));assertFalse(RolePolicy.remove("RESPONSABLE"));assertFalse(RolePolicy.remove("SECRETARIA"));assertFalse(RolePolicy.remove("SUPERADMIN"));}
 @Test public void responsableAccessRemainsRestricted(){assertFalse(RolePolicy.documents("RESPONSABLE",true));}
}
