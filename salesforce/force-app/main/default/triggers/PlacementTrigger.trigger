/**
 * Manté al dia el nombre de contractes actius de cada client (Account.Active_Placements__c).
 * La lògica viu a PlacementTriggerHandler: el trigger només delega.
 */
trigger PlacementTrigger on Placement__c (after insert, after update, after delete, after undelete) {
    PlacementTriggerHandler.recalculateActivePlacements(Trigger.new, Trigger.old);
}
