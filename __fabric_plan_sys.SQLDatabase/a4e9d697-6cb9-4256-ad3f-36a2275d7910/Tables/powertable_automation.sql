CREATE TABLE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[powertable_automation] (
    [id]              INT            IDENTITY (1, 1) NOT NULL,
    [name]            VARCHAR (255)  NOT NULL,
    [sourceId]        INT            NOT NULL,
    [triggerType]     INT            NOT NULL,
    [config]          NVARCHAR (MAX) NOT NULL,
    [configUpdatedAt] INT            NULL,
    [status]          INT            CONSTRAINT [DF_09ad5dc3ec49abe42add1e70693] DEFAULT ((10)) NOT NULL,
    [createdBy]       NVARCHAR (128) NOT NULL,
    [updatedBy]       NVARCHAR (128) NOT NULL,
    [createdAt]       INT            NOT NULL,
    [updatedAt]       INT            NOT NULL,
    CONSTRAINT [PK_07e827ae5ed8868fafbdcbbb8a1] PRIMARY KEY CLUSTERED ([id] ASC),
    CONSTRAINT [FK_84f71feccc1ee888ab03a46330c] FOREIGN KEY ([sourceId]) REFERENCES [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[powertable_source] ([id])
);


GO

