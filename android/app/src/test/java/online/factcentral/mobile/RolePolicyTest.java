package online.factcentral.mobile;
import org.junit.Test;
import static org.junit.Assert.*;
public class RolePolicyTest {
 @Test public void sevenRoles(){assertEquals(7,RolePolicy.ROLES.size());for(String r:RolePolicy.ROLES)assertEquals(!r.equals("SUPERADMIN"),RolePolicy.operational(r));}
 @Test public void secretariatFailsClosed(){assertFalse(RolePolicy.documents("SECRETARIA",false));assertFalse(RolePolicy.expedients("SECRETARIA",false));assertTrue(RolePolicy.documents("SECRETARIA",true));}
 @Test public void restrictedDocuments(){assertFalse(RolePolicy.documents("GERENTE",true));assertFalse(RolePolicy.documents("RESPONSABLE",true));assertFalse(RolePolicy.documents("SUPERADMIN",true));assertFalse(RolePolicy.operational("UNKNOWN"));}
}
